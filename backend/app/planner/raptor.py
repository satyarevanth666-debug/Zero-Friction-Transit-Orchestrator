"""Deterministic Round-Based Public Transit Routing (RAPTOR) engine.

Supports:
- Multi-modal rounds k=1..3 (direct, 1 transfer, 2 transfers)
- Timetable active calendar validation (run_days bitmask, calendar exceptions)
- Layover buffers (min 30 min, cross-station min 75 min, max 240 min)
- Domestic flight 90-minute check-in buffer
- Transfer edge walk / auto-rickshaw links from DB
- Strict 2-second timeout enforcement
- NULL-safe fare resolution
"""

import time
import uuid
from datetime import date, datetime
from typing import Any, cast

import structlog
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    Fare,
    Service,
    Station,
    TransferEdge,
)
from app.db.session import SessionLocal
from app.planner.scoring import (
    compute_itinerary_reliability,
    compute_leg_reliability,
    compute_transfer_safety,
    is_late_night_hour,
)
from app.schemas.intent import TripIntent
from app.schemas.itinerary import Itinerary, Leg, TransferDetail, TruthLevel

logger = structlog.get_logger("zero-friction-transit")


def parse_time_to_minutes(time_str: str, day_offset: int = 0) -> int:
    """Convert 'HH:MM:SS' or 'HH:MM' with day_offset to minutes from departure midnight."""
    parts = time_str.strip().split(":")
    hrs = int(parts[0])
    mins = int(parts[1]) if len(parts) > 1 else 0
    return (day_offset * 1440) + (hrs * 60) + mins


def format_minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to 'HH:MM' string (handles next-day +1d)."""
    normalized = minutes % 1440
    day_offset = minutes // 1440
    hrs = normalized // 60
    mins = normalized % 60
    suffix = f" (+{day_offset}d)" if day_offset > 0 else ""
    return f"{hrs:02d}:{mins:02d}{suffix}"


class RaptorRouter:
    """Pure-Python deterministic RAPTOR engine for multi-modal travel across India."""

    def __init__(self, db_session: Session | None = None) -> None:
        self.db = db_session

    def plan(
        self,
        intent: TripIntent,
        db: Session | None = None,
        timeout_seconds: float = 2.0,
    ) -> list[Itinerary]:
        """
        Execute RAPTOR search for given trip intent.
        Returns list of valid multi-modal itineraries within hard timeout.
        """
        start_mono = time.monotonic()
        session = db or self.db or SessionLocal()
        should_close = db is None and self.db is None

        try:
            # 1. Resolve Origin and Destination station codes
            origin_codes = self._get_station_codes(intent, is_origin=True, session=session)
            dest_codes = self._get_station_codes(intent, is_origin=False, session=session)

            if not origin_codes or not dest_codes:
                logger.warning(
                    "Missing origin or destination station codes for search",
                    origins=origin_codes,
                    dests=dest_codes,
                )
                return []

            # 2. Parse travel date and earliest departure
            travel_date = self._parse_travel_date(intent.departure_date)
            earliest_dep_min = 0
            latest_dep_min = 2880  # 48 hours

            if intent.time_range:
                earliest_dep_min = parse_time_to_minutes(intent.time_range.start_time)
                latest_dep_min = parse_time_to_minutes(intent.time_range.end_time)
                # Expand latest departure if user specified evening window
                if latest_dep_min < earliest_dep_min:
                    latest_dep_min += 1440

            # 3. Load active services and transfer edges
            services = self._load_active_services(session, travel_date, intent.excluded_modes)
            transfer_edges_map = self._load_transfer_edges(session)
            station_info = self._load_station_info(session)

            # 4. Multi-modal RAPTOR Rounds
            # k=1 (direct, 0 transfers), k=2 (1 transfer), k=3 (2 transfers)
            max_rounds = 1 if intent.direct_only else 3
            collected_itineraries: list[Itinerary] = []

            # Round 1: Direct trips
            round1_trips = self._find_direct_trips(
                services=services,
                origin_codes=origin_codes,
                dest_codes=dest_codes,
                travel_date=travel_date,
                earliest_dep=earliest_dep_min,
                latest_dep=latest_dep_min,
                station_info=station_info,
                session=session,
                class_preference=intent.class_preference,
            )
            collected_itineraries.extend(round1_trips)

            # If direct_only or timeout, exit early
            if max_rounds <= 1 or (time.monotonic() - start_mono) >= timeout_seconds:
                return collected_itineraries

            # Round 2: 1 Transfer (Leg 1 -> Layover/Transfer -> Leg 2)
            round2_trips = self._find_two_leg_trips(
                services=services,
                origin_codes=origin_codes,
                dest_codes=dest_codes,
                travel_date=travel_date,
                earliest_dep=earliest_dep_min,
                latest_dep=latest_dep_min,
                transfer_edges_map=transfer_edges_map,
                station_info=station_info,
                session=session,
                class_preference=intent.class_preference,
                start_mono=start_mono,
                timeout_seconds=timeout_seconds,
            )
            collected_itineraries.extend(round2_trips)

            # Check timeout before Round 3
            if max_rounds >= 3 and (time.monotonic() - start_mono) < (timeout_seconds * 0.85):
                round3_trips = self._find_three_leg_trips(
                    services=services,
                    origin_codes=origin_codes,
                    dest_codes=dest_codes,
                    travel_date=travel_date,
                    earliest_dep=earliest_dep_min,
                    latest_dep=latest_dep_min,
                    transfer_edges_map=transfer_edges_map,
                    station_info=station_info,
                    session=session,
                    class_preference=intent.class_preference,
                    start_mono=start_mono,
                    timeout_seconds=timeout_seconds,
                )
                collected_itineraries.extend(round3_trips)

            return collected_itineraries

        finally:
            if should_close:
                session.close()

    def _get_station_codes(
        self,
        intent: TripIntent,
        is_origin: bool,
        session: Session,
    ) -> list[str]:
        """Collect all station codes for origin or destination (including cluster members)."""
        codes: list[str] = []
        if is_origin:
            if intent.origin_station_code:
                codes.append(intent.origin_station_code)
            codes.extend(intent.origin_cluster)
            name = intent.origin
        else:
            if intent.destination_station_code:
                codes.append(intent.destination_station_code)
            codes.extend(intent.destination_cluster)
            name = intent.destination

        # If codes empty but name given, search DB by name or code
        if not codes and name:
            matched_st = session.query(Station).filter(
                (Station.code == name.upper()) | (Station.name.ilike(f"%{name}%"))
            ).all()
            for st in matched_st:
                codes.append(st.code)

        return list(dict.fromkeys(codes))  # Deduplicate

    def _parse_travel_date(self, dep_date_str: str | None) -> date:
        """Parse ISO date string or default to current date."""
        if dep_date_str:
            try:
                return datetime.strptime(dep_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        return date.today()

    def _load_active_services(
        self,
        session: Session,
        travel_date: date,
        excluded_modes: list[str],
    ) -> list[Service]:
        """Fetch all services operating on the travel date excluding user-avoided modes."""
        query = session.query(Service)
        if excluded_modes:
            query = query.filter(~Service.mode.in_(excluded_modes))

        all_services = query.all()
        weekday = travel_date.weekday()
        day_mask = 1 << weekday

        active: list[Service] = []
        for s in all_services:
            # Check calendar exceptions first
            exc = next((e for e in s.calendar_exceptions if e.exception_date == travel_date), None)
            if exc:
                if exc.exception_type == 1:
                    active.append(s)
                continue

            # Check calendar validity
            if s.calendar:
                if s.calendar.valid_from <= travel_date <= s.calendar.valid_to and (s.calendar.run_days & day_mask):
                    active.append(s)
            else:
                active.append(s)

        return active

    def _load_transfer_edges(self, session: Session) -> dict[tuple[str, str], TransferEdge]:
        """Map (from_code, to_code) -> TransferEdge."""
        edges = session.query(TransferEdge).all()
        return {(e.from_station_code, e.to_station_code): e for e in edges}

    def _load_station_info(self, session: Session) -> dict[str, dict[str, Any]]:
        """Map station_code -> {id, name, type, city_id}."""
        stations = session.query(Station).all()
        return {
            st.code: {
                "id": st.id,
                "name": st.name,
                "type": st.type,
                "city_id": st.city_id,
            }
            for st in stations
        }

    def _find_direct_trips(
        self,
        services: list[Service],
        origin_codes: list[str],
        dest_codes: list[str],
        travel_date: date,
        earliest_dep: int,
        latest_dep: int,
        station_info: dict[str, dict[str, Any]],
        session: Session,
        class_preference: list[str],
    ) -> list[Itinerary]:
        """Find direct (k=1) single-leg connections."""
        itineraries: list[Itinerary] = []
        orig_set = set(origin_codes)
        dest_set = set(dest_codes)

        # Invert station_info: id -> code
        st_id_to_code = {v["id"]: k for k, v in station_info.items()}

        for s in services:
            stop_times = sorted(s.stop_times, key=lambda x: x.seq)
            st_seq = [(st_id_to_code.get(st.station_id, ""), st) for st in stop_times]

            # Search pairs (i, j) with i < j
            for i, (orig_code, st_orig) in enumerate(st_seq):
                if orig_code in orig_set:
                    dep_min = parse_time_to_minutes(st_orig.depart, st_orig.day_offset)
                    if dep_min < earliest_dep or dep_min > latest_dep:
                        continue

                    for j in range(i + 1, len(st_seq)):
                        dest_code, st_dest = st_seq[j]
                        if dest_code in dest_set:
                            arr_min = parse_time_to_minutes(st_dest.arrive, st_dest.day_offset)
                            if arr_min <= dep_min:
                                continue

                            duration = arr_min - dep_min
                            fare_val, truth_lvl, cls_cd = self._lookup_fare(
                                session=session,
                                service_id=s.id,
                                from_code=orig_code,
                                to_code=dest_code,
                                class_preference=class_preference,
                            )

                            leg = Leg(
                                mode=s.mode,
                                operator=s.operator,
                                service_number=s.number,
                                service_name=s.name,
                                from_station_code=orig_code,
                                from_station_name=station_info.get(orig_code, {}).get("name", orig_code),
                                to_station_code=dest_code,
                                to_station_name=station_info.get(dest_code, {}).get("name", dest_code),
                                departure_time=format_minutes_to_time(dep_min),
                                arrival_time=format_minutes_to_time(arr_min),
                                duration_minutes=duration,
                                fare_inr=fare_val,
                                truth_level=truth_lvl,
                                class_code=cls_cd,
                            )
                            leg.reliability_score = compute_leg_reliability(leg)

                            it = Itinerary(
                                id=str(uuid.uuid4())[:8],
                                legs=[leg],
                                transfers=[],
                                total_duration_minutes=duration,
                                departure_time=leg.departure_time,
                                arrival_time=leg.arrival_time,
                                total_fare_inr=fare_val,
                                is_fare_verified=(fare_val is not None),
                                transfers_count=0,
                                overall_reliability_score=leg.reliability_score,
                                badges=[leg.truth_level],
                            )
                            itineraries.append(it)

        return itineraries

    def _find_two_leg_trips(
        self,
        services: list[Service],
        origin_codes: list[str],
        dest_codes: list[str],
        travel_date: date,
        earliest_dep: int,
        latest_dep: int,
        transfer_edges_map: dict[tuple[str, str], TransferEdge],
        station_info: dict[str, dict[str, Any]],
        session: Session,
        class_preference: list[str],
        start_mono: float,
        timeout_seconds: float,
    ) -> list[Itinerary]:
        """Find 2-leg itineraries with 1 intermediate transfer."""
        itineraries: list[Itinerary] = []
        orig_set = set(origin_codes)
        dest_set = set(dest_codes)
        st_id_to_code = {v["id"]: k for k, v in station_info.items()}

        # 1. Collect candidate first legs from origin
        first_legs: list[tuple[Service, str, str, int, int]] = []
        for s in services:
            st_seq = [(st_id_to_code.get(st.station_id, ""), st) for st in sorted(s.stop_times, key=lambda x: x.seq)]
            for i, (orig_code, st_orig) in enumerate(st_seq):
                if orig_code in orig_set:
                    dep_min = parse_time_to_minutes(st_orig.depart, st_orig.day_offset)
                    if dep_min < earliest_dep or dep_min > latest_dep:
                        continue
                    for j in range(i + 1, len(st_seq)):
                        transfer_station_code, st_transfer = st_seq[j]
                        if transfer_station_code not in dest_set:
                            arr_min = parse_time_to_minutes(st_transfer.arrive, st_transfer.day_offset)
                            if arr_min > dep_min:
                                first_legs.append((s, orig_code, transfer_station_code, dep_min, arr_min))

        # 2. Match with second legs reaching destination
        for s1, orig_c, mid_arr_c, dep1, arr1 in first_legs:
            # Check timeout
            if (time.monotonic() - start_mono) >= timeout_seconds:
                break

            # Find possible departure stations from mid_arr_c (same station or transfer edge)
            candidate_mid_deps: list[tuple[str, int, float, bool]] = [(mid_arr_c, 0, 0.0, False)]
            for (f_code, t_code), edge in transfer_edges_map.items():
                if f_code == mid_arr_c:
                    candidate_mid_deps.append((t_code, edge.minutes, edge.cost_inr or 0.0, True))

            for mid_dep_c, edge_mins, edge_cost, is_cross in candidate_mid_deps:
                for s2 in services:
                    if s2.id == s1.id:
                        continue  # Avoid boarding the exact same service instance

                    st_seq2 = [(st_id_to_code.get(st.station_id, ""), st) for st in sorted(s2.stop_times, key=lambda x: x.seq)]
                    for m, (b_code, st_b) in enumerate(st_seq2):
                        if b_code == mid_dep_c:
                            dep2 = parse_time_to_minutes(st_b.depart, st_b.day_offset)
                            buffer_mins = dep2 - arr1

                            # Check buffer feasibility
                            # Same station: min 30 min, max 240 min
                            # Cross station: min 75 min (or edge_mins + 30), max 240 min
                            # Flight: min 90 min check-in
                            min_buffer = 30
                            if is_cross:
                                min_buffer = max(75, edge_mins + 30)
                            if s2.mode == "flight":
                                min_buffer = max(min_buffer, settings.DOMESTIC_CHECKIN_BUFFER_MIN)

                            if buffer_mins < min_buffer or buffer_mins > 240:
                                continue

                            for n in range(m + 1, len(st_seq2)):
                                dest_c, st_dest2 = st_seq2[n]
                                if dest_c in dest_set:
                                    arr2 = parse_time_to_minutes(st_dest2.arrive, st_dest2.day_offset)
                                    if arr2 <= dep2:
                                        continue

                                    # Valid 2-leg itinerary found!
                                    it = self._build_multi_leg_itinerary(
                                        session=session,
                                        legs_data=[
                                            (s1, orig_c, mid_arr_c, dep1, arr1),
                                            (s2, mid_dep_c, dest_c, dep2, arr2),
                                        ],
                                        transfers_data=[
                                            (mid_arr_c, mid_dep_c, buffer_mins, is_cross, edge_cost)
                                        ],
                                        station_info=station_info,
                                        class_preference=class_preference,
                                    )
                                    if it:
                                        itineraries.append(it)

        return itineraries

    def _find_three_leg_trips(
        self,
        services: list[Service],
        origin_codes: list[str],
        dest_codes: list[str],
        travel_date: date,
        earliest_dep: int,
        latest_dep: int,
        transfer_edges_map: dict[tuple[str, str], TransferEdge],
        station_info: dict[str, dict[str, Any]],
        session: Session,
        class_preference: list[str],
        start_mono: float,
        timeout_seconds: float,
    ) -> list[Itinerary]:
        """Find 3-leg itineraries with 2 intermediate transfers (k=3)."""
        # Kept lean with strict timeout checks for deep multi-modal hubs
        itineraries: list[Itinerary] = []
        dest_set = set(dest_codes)
        st_id_to_code = {v["id"]: k for k, v in station_info.items()}

        # Build candidate pairs from first legs
        two_leg_candidates: list[tuple[Service, str, str, int, int, Service, str, str, int, int, int, bool, float]] = []

        # Find 2 legs first
        for s1 in services:
            if (time.monotonic() - start_mono) >= (timeout_seconds * 0.9):
                break
            st_seq1 = [(st_id_to_code.get(st.station_id, ""), st) for st in sorted(s1.stop_times, key=lambda x: x.seq)]
            for i, (orig_c, st_orig) in enumerate(st_seq1):
                if orig_c in origin_codes:
                    dep1 = parse_time_to_minutes(st_orig.depart, st_orig.day_offset)
                    if dep1 < earliest_dep or dep1 > latest_dep:
                        continue
                    for j in range(i + 1, len(st_seq1)):
                        mid1_arr_c, st_m1 = st_seq1[j]
                        arr1 = parse_time_to_minutes(st_m1.arrive, st_m1.day_offset)
                        if arr1 <= dep1 or mid1_arr_c in dest_set:
                            continue

                        # Second leg
                        for s2 in services:
                            if s2.id == s1.id:
                                continue
                            st_seq2 = [(st_id_to_code.get(st.station_id, ""), st) for st in sorted(s2.stop_times, key=lambda x: x.seq)]
                            for m, (mid1_dep_c, st_m1_dep) in enumerate(st_seq2):
                                is_cross1 = (mid1_arr_c != mid1_dep_c)
                                if not is_cross1 or (mid1_arr_c, mid1_dep_c) in transfer_edges_map:
                                    dep2 = parse_time_to_minutes(st_m1_dep.depart, st_m1_dep.day_offset)
                                    buf1 = dep2 - arr1
                                    min_b1 = 75 if is_cross1 else 30
                                    if 30 <= buf1 <= 240 and buf1 >= min_b1:
                                        for n in range(m + 1, len(st_seq2)):
                                            mid2_arr_c, st_m2 = st_seq2[n]
                                            arr2 = parse_time_to_minutes(st_m2.arrive, st_m2.day_offset)
                                            if arr2 > dep2 and mid2_arr_c not in dest_set:
                                                two_leg_candidates.append(
                                                    (s1, orig_c, mid1_arr_c, dep1, arr1, s2, mid1_dep_c, mid2_arr_c, dep2, arr2, buf1, is_cross1, 0.0)
                                                )
                                                if len(two_leg_candidates) >= 50:
                                                    break

        # Match candidate 2-legs with 3rd leg reaching destination
        for (s1, o_c, m1_a, dep1, arr1, s2, m1_d, m2_a, dep2, arr2, b1, cr1, c1) in two_leg_candidates:
            if (time.monotonic() - start_mono) >= timeout_seconds:
                break
            for s3 in services:
                if s3.id in (s1.id, s2.id):
                    continue
                st_seq3 = [(st_id_to_code.get(st.station_id, ""), st) for st in sorted(s3.stop_times, key=lambda x: x.seq)]
                for p, (m2_d, st_m2_d) in enumerate(st_seq3):
                    is_cross2 = (m2_a != m2_d)
                    if not is_cross2 or (m2_a, m2_d) in transfer_edges_map:
                        dep3 = parse_time_to_minutes(st_m2_d.depart, st_m2_d.day_offset)
                        buf2 = dep3 - arr2
                        min_b2 = 75 if is_cross2 else 30
                        if 30 <= buf2 <= 240 and buf2 >= min_b2:
                            for q in range(p + 1, len(st_seq3)):
                                dest_c, st_dest3 = st_seq3[q]
                                if dest_c in dest_set:
                                    arr3 = parse_time_to_minutes(st_dest3.arrive, st_dest3.day_offset)
                                    if arr3 > dep3:
                                        it = self._build_multi_leg_itinerary(
                                            session=session,
                                            legs_data=[
                                                (s1, o_c, m1_a, dep1, arr1),
                                                (s2, m1_d, m2_a, dep2, arr2),
                                                (s3, m2_d, dest_c, dep3, arr3),
                                            ],
                                            transfers_data=[
                                                (m1_a, m1_d, b1, cr1, c1),
                                                (m2_a, m2_d, buf2, is_cross2, 0.0),
                                            ],
                                            station_info=station_info,
                                            class_preference=class_preference,
                                        )
                                        if it:
                                            itineraries.append(it)

        return itineraries

    def _build_multi_leg_itinerary(
        self,
        session: Session,
        legs_data: list[tuple[Service, str, str, int, int]],
        transfers_data: list[tuple[str, str, int, bool, float]],
        station_info: dict[str, dict[str, Any]],
        class_preference: list[str],
    ) -> Itinerary | None:
        """Assemble Leg and TransferDetail objects into a verified Itinerary."""
        legs: list[Leg] = []
        transfers: list[TransferDetail] = []
        total_fare: float | None = 0.0
        is_fare_verified = True
        badges: set[str] = set()

        for s, from_c, to_c, dep_m, arr_m in legs_data:
            fare_val, truth_lvl, cls_cd = self._lookup_fare(
                session=session,
                service_id=s.id,
                from_code=from_c,
                to_code=to_c,
                class_preference=class_preference,
            )

            leg = Leg(
                mode=s.mode,
                operator=s.operator,
                service_number=s.number,
                service_name=s.name,
                from_station_code=from_c,
                from_station_name=station_info.get(from_c, {}).get("name", from_c),
                to_station_code=to_c,
                to_station_name=station_info.get(to_c, {}).get("name", to_c),
                departure_time=format_minutes_to_time(dep_m),
                arrival_time=format_minutes_to_time(arr_m),
                duration_minutes=arr_m - dep_m,
                fare_inr=fare_val,
                truth_level=truth_lvl,
                class_code=cls_cd,
            )
            leg.reliability_score = compute_leg_reliability(leg)
            legs.append(leg)
            badges.add(truth_lvl)

            if fare_val is not None and total_fare is not None:
                total_fare += fare_val
            else:
                total_fare = None
                is_fare_verified = False

        for f_c, t_c, buf_min, is_cross, edge_cost in transfers_data:
            is_ln = is_late_night_hour(format_minutes_to_time(buf_min))
            safety = compute_transfer_safety(buf_min, is_cross_station=is_cross, is_late_night=is_ln)
            if safety <= 0.0:
                return None  # Infeasible transfer -> discard entire itinerary

            transfers.append(
                TransferDetail(
                    from_station_code=f_c,
                    to_station_code=t_c,
                    buffer_minutes=buf_min,
                    transfer_type="cross_station" if is_cross else "same_station",
                    safety_score=safety,
                    cost_inr=edge_cost if edge_cost > 0 else None,
                )
            )
            if edge_cost > 0 and total_fare is not None:
                total_fare += edge_cost

        overall_rel = compute_itinerary_reliability(legs, transfers)
        first_dep = legs[0].departure_time
        last_arr = legs[-1].arrival_time
        total_duration = legs_data[-1][4] - legs_data[0][3]

        return Itinerary(
            id=str(uuid.uuid4())[:8],
            legs=legs,
            transfers=transfers,
            total_duration_minutes=total_duration,
            departure_time=first_dep,
            arrival_time=last_arr,
            total_fare_inr=round(total_fare, 2) if total_fare is not None else None,
            is_fare_verified=is_fare_verified,
            transfers_count=len(transfers),
            overall_reliability_score=overall_rel,
            badges=sorted(badges),
        )

    def _lookup_fare(
        self,
        session: Session,
        service_id: str,
        from_code: str,
        to_code: str,
        class_preference: list[str],
    ) -> tuple[float | None, TruthLevel, str | None]:
        """Lookup station-to-station fare for preferred class or best available."""
        query = session.query(Fare).filter(
            Fare.service_id == service_id,
            Fare.from_station_code == from_code,
            Fare.to_station_code == to_code,
        )

        fares = query.all()
        if not fares:
            # Honest NULL-safe fallback
            return None, "UNKNOWN", None

        # Try to find user's preferred class
        if class_preference:
            for pref in class_preference:
                matched = next((f for f in fares if f.class_code.upper() == pref.upper()), None)
                if matched:
                    tl: TruthLevel = (
                        cast(TruthLevel, matched.truth_level)
                        if matched.truth_level in (
                            "OFFICIAL_TIMETABLE", "COMMUNITY_GTFS", "LIVE_API",
                            "ESTIMATED", "USER_PROVIDED", "UNKNOWN"
                        )
                        else "UNKNOWN"
                    )
                    return matched.amount_inr, tl, matched.class_code

        # Default to lowest available standard fare
        sorted_fares = sorted(
            fares,
            key=lambda f: (f.amount_inr is None, f.amount_inr if f.amount_inr is not None else float("inf")),
        )
        first_fare = sorted_fares[0]
        first_tl: TruthLevel = (
            cast(TruthLevel, first_fare.truth_level)
            if first_fare.truth_level in (
                "OFFICIAL_TIMETABLE", "COMMUNITY_GTFS", "LIVE_API",
                "ESTIMATED", "USER_PROVIDED", "UNKNOWN"
            )
            else "UNKNOWN"
        )
        return first_fare.amount_inr, first_tl, first_fare.class_code


default_raptor_router = RaptorRouter()

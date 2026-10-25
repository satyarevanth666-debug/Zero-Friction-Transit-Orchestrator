"""Generic GTFS zip loader with strict schema validation and error logging."""

import csv
import hashlib
import io
import os
import zipfile
from datetime import UTC, date, datetime
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.db.models import (
    Calendar,
    CalendarException,
    DataSource,
    Service,
    Station,
    StopTime,
)
from app.providers.base import ImportResult, TransitProvider

logger = structlog.get_logger("zero-friction-transit")


def normalize_gtfs_time(time_str: str) -> tuple[str, int]:
    """
    Parse and normalize GTFS HH:MM:SS format, handling times beyond 24:00:00.
    
    Returns:
        (normalized_time_str, day_offset)
    Raises:
        ValueError if time is negative or exceeds 48:00:00.
    """
    parts = time_str.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid time format: '{time_str}', expected HH:MM:SS")

    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    if h < 0 or m < 0 or m >= 60 or s < 0 or s >= 60:
        raise ValueError(f"Out-of-range time values in '{time_str}'")

    if h >= 48:
        raise ValueError(f"Time exceeds maximum supported 48:00:00 threshold: '{time_str}'")

    day_offset = h // 24
    normalized_h = h % 24
    normalized_time = f"{normalized_h:02d}:{m:02d}:{s:02d}"
    return normalized_time, day_offset


def time_to_seconds(time_str: str, day_offset: int) -> int:
    """Convert normalized HH:MM:SS and day_offset into absolute seconds from day 0 midnight."""
    h, m, s = (int(x) for x in time_str.split(":"))
    return day_offset * 86400 + h * 3600 + m * 60 + s


def parse_gtfs_date(date_str: str) -> date:
    """Parse GTFS YYYYMMDD string into a datetime.date."""
    clean = date_str.strip()
    return date(int(clean[0:4]), int(clean[4:6]), int(clean[6:8]))


class GtfsProvider(TransitProvider):
    """Generic GTFS Feed Provider for Rail and Regional Bus feeds."""

    def __init__(
        self,
        provider_id: str,
        name: str,
        mode: str,
        truth_level: str,
        license_name: str,
        file_path: str | None = None,
        enabled: bool = True,
        rejects_csv_path: str = "data/rejects.csv",
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            name=name,
            mode=mode,
            truth_level=truth_level,
            license_name=license_name,
            enabled=enabled,
        )
        self.file_path = file_path
        self.rejects_csv_path = rejects_csv_path

    def _log_reject(
        self,
        row_type: str,
        identifier: str,
        reason: str,
        raw_content: str,
    ) -> None:
        """Log invalid data row to rejects.csv."""
        logger.warning(
            "GTFS row rejected",
            provider=self.provider_id,
            row_type=row_type,
            identifier=identifier,
            reason=reason,
        )
        try:
            from app.config import resolve_data_path
            actual_csv = resolve_data_path(self.rejects_csv_path)
            os.makedirs(os.path.dirname(actual_csv) or ".", exist_ok=True)
            file_exists = os.path.exists(actual_csv)
            with open(actual_csv, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:

                    writer.writerow(["timestamp", "provider_id", "row_type", "identifier", "reason", "raw_content"])
                writer.writerow([
                    datetime.now(UTC).isoformat(),
                    self.provider_id,
                    row_type,
                    identifier,
                    reason,
                    raw_content.replace("\n", " ").strip(),
                ])
        except OSError as e:
            logger.error("Failed to append to rejects.csv", error=str(e))


    def fetch_static(self, db: Session, file_path: str | None = None) -> ImportResult:
        """Parse GTFS zip file and persist normalized services into database."""
        from app.config import resolve_data_path
        target_path = resolve_data_path(file_path or self.file_path or "")
        result = ImportResult(provider_id=self.provider_id)

        if not target_path or not os.path.exists(target_path):
            error_msg = f"GTFS archive file not found at: {target_path}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return result


        # Compute SHA-256 Checksum
        with open(target_path, "rb") as f:
            content_bytes = f.read()
            checksum = hashlib.sha256(content_bytes).hexdigest()
            result.checksum = checksum

        try:
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as z:
                namelist = z.namelist()

                # Read Agency for Operator Name
                operator = self.name
                if "agency.txt" in namelist:
                    with z.open("agency.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            operator = row.get("agency_name", operator)
                            break

                # Read Stops into local map and ensure Station records exist
                stops_map: dict[str, int] = {}  # stop_id -> station.id
                if "stops.txt" in namelist:
                    with z.open("stops.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            stop_id = row["stop_id"].strip()
                            stop_name = row.get("stop_name", stop_id).strip()
                            lat = float(row.get("stop_lat", 0.0))
                            lon = float(row.get("stop_lon", 0.0))

                            # Find or create Station
                            station = db.query(Station).filter(Station.code == stop_id).first()
                            if not station:
                                station = Station(
                                    code=stop_id,
                                    name=stop_name,
                                    type=self.mode if self.mode in ("rail", "bus_stand", "airport") else "rail",
                                    lat=lat,
                                    lon=lon,
                                )
                                db.add(station)
                                db.flush()
                            stops_map[stop_id] = station.id

                # Read Routes
                routes_map: dict[str, dict[str, str]] = {}
                if "routes.txt" in namelist:
                    with z.open("routes.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            r_id = row["route_id"].strip()
                            r_short = row.get("route_short_name", "").strip()
                            r_long = row.get("route_long_name", "").strip()
                            routes_map[r_id] = {"short": r_short, "long": r_long}

                # Read Trips
                trips_map: dict[str, dict[str, str]] = {}
                if "trips.txt" in namelist:
                    with z.open("trips.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            t_id = row["trip_id"].strip()
                            r_id = row["route_id"].strip()
                            s_id = row["service_id"].strip()
                            headsign = row.get("trip_headsign", "").strip()
                            trips_map[t_id] = {
                                "route_id": r_id,
                                "service_id": s_id,
                                "headsign": headsign,
                            }

                # Read Calendar
                calendars_map: dict[str, dict[str, Any]] = {}
                min_valid_from: date | None = None
                max_valid_to: date | None = None

                if "calendar.txt" in namelist:
                    with z.open("calendar.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            s_id = row["service_id"].strip()
                            v_from = parse_gtfs_date(row["start_date"])
                            v_to = parse_gtfs_date(row["end_date"])

                            # Calculate run_days bitmask
                            # Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64
                            bitmask = 0
                            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                            for i, d in enumerate(days):
                                if row.get(d, "0").strip() == "1":
                                    bitmask |= (1 << i)

                            calendars_map[s_id] = {
                                "run_days": bitmask,
                                "valid_from": v_from,
                                "valid_to": v_to,
                            }

                            if min_valid_from is None or v_from < min_valid_from:
                                min_valid_from = v_from
                            if max_valid_to is None or v_to > max_valid_to:
                                max_valid_to = v_to

                # Read Calendar Exceptions
                exceptions_map: dict[str, list[tuple[date, int]]] = {}
                if "calendar_dates.txt" in namelist:
                    with z.open("calendar_dates.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            s_id = row["service_id"].strip()
                            e_date = parse_gtfs_date(row["date"])
                            e_type = int(row["exception_type"])
                            exceptions_map.setdefault(s_id, []).append((e_date, e_type))

                # Read Stop Times and Validate
                trip_stop_times: dict[str, list[dict[str, Any]]] = {}
                if "stop_times.txt" in namelist:
                    with z.open("stop_times.txt") as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                        for row in reader:
                            t_id = row.get("trip_id", "").strip()
                            stop_id = row.get("stop_id", "").strip()
                            arr_str = row.get("arrival_time", "").strip()
                            dep_str = row.get("departure_time", "").strip()
                            seq_str = row.get("stop_sequence", "").strip()

                            # 1. Validation: Orphan stop check
                            if stop_id not in stops_map:
                                self._log_reject(
                                    row_type="stop_time",
                                    identifier=f"{t_id}:{stop_id}",
                                    reason=f"Orphan stop '{stop_id}' not found in stops.txt",
                                    raw_content=str(row),
                                )
                                result.rejected_rows += 1
                                continue

                            # 2. Validation: Time formatting & >48h checks
                            try:
                                norm_arr, arr_offset = normalize_gtfs_time(arr_str)
                                norm_dep, dep_offset = normalize_gtfs_time(dep_str)
                                seq = int(seq_str)
                            except ValueError as ve:
                                self._log_reject(
                                    row_type="stop_time",
                                    identifier=f"{t_id}:{stop_id}",
                                    reason=str(ve),
                                    raw_content=str(row),
                                )
                                result.rejected_rows += 1
                                continue

                            # 3. Validation: Negative dwell time within same stop
                            arr_secs = time_to_seconds(norm_arr, arr_offset)
                            dep_secs = time_to_seconds(norm_dep, dep_offset)
                            if dep_secs < arr_secs:
                                self._log_reject(
                                    row_type="stop_time",
                                    identifier=f"{t_id}:{stop_id}",
                                    reason=f"Negative dwell time: departure ({dep_str}) precedes arrival ({arr_str})",
                                    raw_content=str(row),
                                )
                                result.rejected_rows += 1
                                continue

                            trip_stop_times.setdefault(t_id, []).append({
                                "stop_id": stop_id,
                                "station_id": stops_map[stop_id],
                                "arrive": norm_arr,
                                "depart": norm_dep,
                                "day_offset": arr_offset,
                                "dep_day_offset": dep_offset,
                                "seq": seq,
                                "arr_secs": arr_secs,
                                "dep_secs": dep_secs,
                            })

                # Check Idempotency: Delete previous records for this source (and related child entities)
                from app.db.models import Fare
                existing_services = db.query(Service.id).filter(Service.source_id == self.provider_id).all()
                svc_ids = [s[0] for s in existing_services]
                if svc_ids:
                    db.query(Calendar).filter(Calendar.service_id.in_(svc_ids)).delete(synchronize_session=False)
                    db.query(CalendarException).filter(CalendarException.service_id.in_(svc_ids)).delete(synchronize_session=False)
                    db.query(StopTime).filter(StopTime.service_id.in_(svc_ids)).delete(synchronize_session=False)
                    db.query(Fare).filter(Fare.service_id.in_(svc_ids)).delete(synchronize_session=False)
                    db.query(Service).filter(Service.source_id == self.provider_id).delete(synchronize_session=False)
                    db.flush()


                # Process valid trips and persist to DB
                today = datetime.now(UTC).date()
                for trip_id, st_list in trip_stop_times.items():
                    if trip_id not in trips_map:
                        continue

                    # Sort by sequence
                    st_list.sort(key=lambda x: x["seq"])

                    # Validate sequence and progressive transit times
                    has_error = False
                    seen_seqs: set[int] = set()
                    for i in range(len(st_list)):
                        cur = st_list[i]
                        if cur["seq"] in seen_seqs:
                            self._log_reject(
                                row_type="trip",
                                identifier=trip_id,
                                reason=f"Duplicate stop sequence {cur['seq']} in trip",
                                raw_content=str(cur),
                            )
                            has_error = True
                            break
                        seen_seqs.add(cur["seq"])

                        if i > 0:
                            prev = st_list[i - 1]
                            # Arrival at current stop must be >= departure at previous stop
                            if cur["arr_secs"] < prev["dep_secs"]:
                                self._log_reject(
                                    row_type="trip",
                                    identifier=trip_id,
                                    reason=f"Negative travel duration between stop {prev['seq']} and {cur['seq']}",
                                    raw_content=f"Prev Dep: {prev['dep_secs']}s, Cur Arr: {cur['arr_secs']}s",
                                )
                                has_error = True
                                break

                    if has_error or len(st_list) < 2:
                        result.rejected_rows += len(st_list)
                        continue

                    trip_info = trips_map[trip_id]
                    route_info = routes_map.get(trip_info["route_id"], {"short": trip_id, "long": ""})
                    service_cal_id = trip_info["service_id"]

                    service_num = route_info["short"] or trip_id
                    service_name = route_info["long"] or trip_info["headsign"] or f"{operator} {service_num}"

                    # Create Service entity
                    service = Service(
                        id=f"{self.provider_id}_{trip_id}",
                        mode=self.mode,
                        operator=operator,
                        number=service_num,
                        name=service_name,
                        source_id=self.provider_id,
                        truth_level=self.truth_level,
                    )
                    db.add(service)
                    result.services_imported += 1

                    # Add StopTimes
                    for st in st_list:
                        stop_time_record = StopTime(
                            service_id=service.id,
                            station_id=st["station_id"],
                            arrive=st["arrive"],
                            depart=st["depart"],
                            day_offset=st["day_offset"],
                            seq=st["seq"],
                        )
                        db.add(stop_time_record)
                        result.stop_times_imported += 1

                    # Add Calendar
                    if service_cal_id in calendars_map:
                        cal_data = calendars_map[service_cal_id]
                        calendar_record = Calendar(
                            service_id=service.id,
                            run_days=cal_data["run_days"],
                            valid_from=cal_data["valid_from"],
                            valid_to=cal_data["valid_to"],
                        )
                        db.add(calendar_record)
                        result.calendars_imported += 1

                    # Add Calendar Exceptions
                    if service_cal_id in exceptions_map:
                        for ex_date, ex_type in exceptions_map[service_cal_id]:
                            ex_record = CalendarException(
                                service_id=service.id,
                                exception_date=ex_date,
                                exception_type=ex_type,
                            )
                            db.add(ex_record)

                # Check Calendar Expiry
                if max_valid_to and max_valid_to < today:
                    result.is_expired = True
                    logger.warning(
                        "Schedule data expired",
                        provider=self.provider_id,
                        valid_to=max_valid_to.isoformat(),
                    )

                result.valid_from = min_valid_from
                result.valid_to = max_valid_to

                # Record Data Source Metadata
                data_source = db.query(DataSource).filter(DataSource.id == self.provider_id).first()
                if not data_source:
                    data_source = DataSource(
                        id=self.provider_id,
                        name=self.name,
                        url=self.file_path,
                        license=self.license,
                        version="1.0",
                        fetched_at=datetime.now(UTC),
                        valid_from=min_valid_from,
                        valid_to=max_valid_to,
                        checksum=checksum,
                        row_count=result.services_imported,
                    )
                    db.add(data_source)
                else:
                    data_source.checksum = checksum
                    data_source.valid_from = min_valid_from
                    data_source.valid_to = max_valid_to
                    data_source.fetched_at = datetime.now(UTC)
                    data_source.row_count = result.services_imported

                db.commit()
                logger.info(
                    "GTFS import finished",
                    provider=self.provider_id,
                    services=result.services_imported,
                    stop_times=result.stop_times_imported,
                    rejected_rows=result.rejected_rows,
                    is_expired=result.is_expired,
                )

        except (OSError, UnicodeDecodeError, zipfile.BadZipFile, KeyError, ValueError, RuntimeError) as e:
            db.rollback()
            logger.error("GTFS import failed", provider=self.provider_id, error=str(e))
            result.errors.append(str(e))


        return result

    def fetch_dynamic(self, query: Any) -> list[Any] | None:
        return None

    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "mode": self.mode,
            "enabled": self.enabled,
            "truth_level": self.truth_level,
            "license": self.license,
            "status": "ready" if self.enabled else "disabled",
        }

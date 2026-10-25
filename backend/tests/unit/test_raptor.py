"""Integration and unit tests for the RAPTOR Multi-modal Routing Engine."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Calendar, Fare, Service, Station, StopTime, TransferEdge
from app.planner.raptor import RaptorRouter
from app.schemas.intent import TripIntent


@pytest.fixture
def raptor_db() -> Session:
    """In-memory SQLite database populated with multi-modal test timetable."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    # 1. Stations
    stations = [
        Station(id=1, code="SBC", name="KSR Bengaluru City", type="rail", lat=12.9784, lon=77.5694),
        Station(id=2, code="DMM", name="Dharmavaram Junction", type="rail", lat=14.4172, lon=77.7180),
        Station(id=3, code="DMM_BUS", name="Dharmavaram Bus Stand", type="bus_stand", lat=14.4110, lon=77.7240),
        Station(id=4, code="BZA", name="Vijayawada Junction", type="rail", lat=16.5186, lon=80.6200),
        Station(id=5, code="BZA_BUS", name="Pandit Nehru Bus Station", type="bus_stand", lat=16.5085, lon=80.6174),
        Station(id=6, code="HYD_AIR", name="Hyderabad Airport", type="airport", lat=17.2403, lon=78.4294),
        Station(id=7, code="DEL_AIR", name="Delhi Airport", type="airport", lat=28.5562, lon=77.1000),
    ]
    session.add_all(stations)

    # 2. Transfer Edges
    transfers = [
        TransferEdge(from_station_code="DMM", to_station_code="DMM_BUS", minutes=12, cost_inr=30),
        TransferEdge(from_station_code="DMM_BUS", to_station_code="DMM", minutes=12, cost_inr=30),
        TransferEdge(from_station_code="BZA", to_station_code="BZA_BUS", minutes=15, cost_inr=50),
        TransferEdge(from_station_code="BZA_BUS", to_station_code="BZA", minutes=15, cost_inr=50),
    ]
    session.add_all(transfers)

    # 3. Services
    # Service 1: Direct Train (SBC -> DMM -> BZA)
    s1 = Service(
        id="SRV_TRAIN_DIRECT",
        mode="rail",
        operator="Indian Railways",
        number="12786",
        name="Bangalore-Vijayawada SF Express",
        source_id="test",
        truth_level="OFFICIAL_TIMETABLE",
    )
    s1.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s1.stop_times = [
        StopTime(station_id=1, arrive="08:00:00", depart="08:00:00", seq=1),  # SBC
        StopTime(station_id=2, arrive="12:00:00", depart="12:05:00", seq=2),  # DMM
        StopTime(station_id=4, arrive="18:00:00", depart="18:00:00", seq=3),  # BZA
    ]
    s1.fares = [
        Fare(from_station_code="SBC", to_station_code="BZA", class_code="SL", amount_inr=450.0, truth_level="OFFICIAL_TIMETABLE"),
        Fare(from_station_code="SBC", to_station_code="BZA", class_code="3A", amount_inr=1200.0, truth_level="OFFICIAL_TIMETABLE"),
        Fare(from_station_code="SBC", to_station_code="DMM", class_code="SL", amount_inr=220.0, truth_level="OFFICIAL_TIMETABLE"),
    ]

    # Service 2: Morning Train (SBC -> DMM) arriving DMM at 10:30
    s2 = Service(
        id="SRV_TRAIN_FEEDER",
        mode="rail",
        operator="Indian Railways",
        number="16593",
        name="Hampi Express",
        source_id="test",
        truth_level="OFFICIAL_TIMETABLE",
    )
    s2.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s2.stop_times = [
        StopTime(station_id=1, arrive="06:30:00", depart="06:30:00", seq=1),  # SBC
        StopTime(station_id=2, arrive="10:30:00", depart="10:35:00", seq=2),  # DMM
    ]
    s2.fares = [
        Fare(from_station_code="SBC", to_station_code="DMM", class_code="SL", amount_inr=200.0, truth_level="OFFICIAL_TIMETABLE"),
    ]

    # Service 3: Connecting APSRTC Bus from DMM_BUS to BZA_BUS departing 12:00 (Buffer = 90 min)
    s3 = Service(
        id="SRV_BUS_CONNECTING",
        mode="bus",
        operator="APSRTC",
        number="AP-6201",
        name="Amaravathi AC Sleeper",
        source_id="test",
        truth_level="COMMUNITY_GTFS",
    )
    s3.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s3.stop_times = [
        StopTime(station_id=3, arrive="12:00:00", depart="12:00:00", seq=1),  # DMM_BUS
        StopTime(station_id=5, arrive="18:30:00", depart="18:30:00", seq=2),  # BZA_BUS
    ]
    s3.fares = [
        Fare(from_station_code="DMM_BUS", to_station_code="BZA_BUS", class_code="EXP", amount_inr=380.0, truth_level="COMMUNITY_GTFS"),
    ]

    # Service 4: Infeasible Bus departing 10:45 (Only 15 min buffer after Train 2 -> Infeasible!)
    s4 = Service(
        id="SRV_BUS_INFEASIBLE_BUFFER",
        mode="bus",
        operator="APSRTC",
        number="AP-9999",
        name="Express Bus",
        source_id="test",
        truth_level="COMMUNITY_GTFS",
    )
    s4.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s4.stop_times = [
        StopTime(station_id=3, arrive="10:45:00", depart="10:45:00", seq=1),  # DMM_BUS
        StopTime(station_id=5, arrive="17:00:00", depart="17:00:00", seq=2),  # BZA_BUS
    ]

    # Service 5: Feeder to Airport (SBC -> HYD_AIR) arriving at 14:00
    s5 = Service(
        id="SRV_FEEDER_AIRPORT",
        mode="bus",
        operator="Pushpak Airport Liner",
        number="AIR-1",
        name="Airport Shuttle",
        source_id="test",
        truth_level="COMMUNITY_GTFS",
    )
    s5.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s5.stop_times = [
        StopTime(station_id=1, arrive="10:00:00", depart="10:00:00", seq=1),
        StopTime(station_id=6, arrive="14:00:00", depart="14:00:00", seq=2),
    ]

    # Service 6: Flight with insufficient check-in buffer (Departs 15:00 -> 60 min < 90 min required)
    s6 = Service(
        id="SRV_FLIGHT_TIGHT",
        mode="flight",
        operator="IndiGo",
        number="6E-101",
        name="IndiGo Flight",
        source_id="test",
        truth_level="LIVE_API",
    )
    s6.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s6.stop_times = [
        StopTime(station_id=6, arrive="15:00:00", depart="15:00:00", seq=1),
        StopTime(station_id=7, arrive="17:15:00", depart="17:15:00", seq=2),
    ]

    # Service 7: Flight with ample check-in buffer (Departs 16:00 -> 120 min >= 90 min required)
    s7 = Service(
        id="SRV_FLIGHT_VALID",
        mode="flight",
        operator="Air India",
        number="AI-505",
        name="Air India Flight",
        source_id="test",
        truth_level="OFFICIAL_TIMETABLE",
    )
    s7.calendar = Calendar(run_days=127, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
    s7.stop_times = [
        StopTime(station_id=6, arrive="16:00:00", depart="16:00:00", seq=1),
        StopTime(station_id=7, arrive="18:15:00", depart="18:15:00", seq=2),
    ]
    s7.fares = [
        Fare(from_station_code="HYD_AIR", to_station_code="DEL_AIR", class_code="ECO", amount_inr=3500.0, truth_level="OFFICIAL_TIMETABLE"),
    ]

    session.add_all([s1, s2, s3, s4, s5, s6, s7])
    session.commit()

    return session


# ==============================================================================
# Tests
# ==============================================================================

def test_raptor_direct_route(raptor_db: Session) -> None:
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Vijayawada Junction",
        origin_station_code="SBC",
        destination_station_code="BZA",
        departure_date="2026-10-30",
        direct_only=True,
    )

    itineraries = router.plan(intent, db=raptor_db)

    assert len(itineraries) == 1
    it = itineraries[0]
    assert it.transfers_count == 0
    assert len(it.legs) == 1
    assert it.legs[0].service_number == "12786"
    assert it.legs[0].from_station_code == "SBC"
    assert it.legs[0].to_station_code == "BZA"
    assert it.total_duration_minutes == 600  # 08:00 to 18:00 = 10 hrs = 600 min
    assert it.total_fare_inr == 450.0       # SL class default


def test_raptor_multi_modal_transfer(raptor_db: Session) -> None:
    """Finds combined Train + APSRTC Bus route with cross-station transfer at Dharmavaram."""
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Vijayawada",
        origin_station_code="SBC",
        destination_station_code="BZA_BUS",
        departure_date="2026-10-30",
        direct_only=False,
    )

    itineraries = router.plan(intent, db=raptor_db)

    # Must find the 2-leg route: Train 16593 to DMM + Bus 6201 from DMM_BUS to BZA_BUS
    assert len(itineraries) >= 1
    multi_leg = next((it for it in itineraries if it.transfers_count == 1), None)
    assert multi_leg is not None
    assert len(multi_leg.legs) == 2
    assert multi_leg.legs[0].mode == "rail"
    assert multi_leg.legs[1].mode == "bus"

    # Verify transfer details
    assert len(multi_leg.transfers) == 1
    tr = multi_leg.transfers[0]
    assert tr.from_station_code == "DMM"
    assert tr.to_station_code == "DMM_BUS"
    assert tr.transfer_type == "cross_station"
    assert tr.buffer_minutes == 90  # Arrive DMM 10:30, Depart DMM_BUS 12:00 = 90 min (>= 75 min required)
    assert tr.cost_inr == 30.0

    # Total fare = Train 200 + Transfer 30 + Bus 380 = 610.0
    assert multi_leg.total_fare_inr == 610.0


def test_raptor_layover_buffer_enforcement(raptor_db: Session) -> None:
    """Service 4 has only 15 min buffer after train arrival; must be rejected as infeasible."""
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Vijayawada",
        origin_station_code="SBC",
        destination_station_code="BZA_BUS",
        departure_date="2026-10-30",
    )

    itineraries = router.plan(intent, db=raptor_db)

    # Ensure no itinerary contains the infeasible AP-9999 service
    for it in itineraries:
        for leg in it.legs:
            assert leg.service_number != "AP-9999"


def test_raptor_domestic_flight_checkin_buffer(raptor_db: Session) -> None:
    """Domestic flights require minimum 90-minute checkin buffer before flight departure."""
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Delhi Airport",
        origin_station_code="SBC",
        destination_station_code="DEL_AIR",
        departure_date="2026-10-30",
    )

    itineraries = router.plan(intent, db=raptor_db)

    # Flight 6E-101 departs at 15:00 (only 60m buffer after 14:00 bus arrival) -> MUST be rejected
    for it in itineraries:
        for leg in it.legs:
            assert leg.service_number != "6E-101"

    # Flight AI-505 departs at 16:00 (120m buffer >= 90m) -> MUST be found
    valid_flight = next((it for it in itineraries if any(l.service_number == "AI-505" for l in it.legs)), None)
    assert valid_flight is not None


def test_raptor_time_limit_enforcement(raptor_db: Session) -> None:
    """Raptor router terminates gracefully within timeout threshold."""
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Vijayawada",
        origin_station_code="SBC",
        destination_station_code="BZA",
        departure_date="2026-10-30",
    )

    # Set very small timeout (e.g. 0.001s)
    itineraries = router.plan(intent, db=raptor_db, timeout_seconds=0.001)
    # Should not crash, returns whatever was found before timeout
    assert isinstance(itineraries, list)


def test_raptor_mode_exclusion(raptor_db: Session) -> None:
    """When user requests 'no buses', bus services are strictly excluded."""
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Vijayawada",
        origin_station_code="SBC",
        destination_station_code="BZA_BUS",
        departure_date="2026-10-30",
        excluded_modes=["bus"],
    )

    itineraries = router.plan(intent, db=raptor_db)

    for it in itineraries:
        for leg in it.legs:
            assert leg.mode != "bus"


def test_raptor_class_preference_matching(raptor_db: Session) -> None:
    """When user specifies 3AC, matching fare is assigned."""
    router = RaptorRouter(db_session=raptor_db)
    intent = TripIntent(
        origin="Bengaluru",
        destination="Vijayawada",
        origin_station_code="SBC",
        destination_station_code="BZA",
        departure_date="2026-10-30",
        class_preference=["3A"],
        direct_only=True,
    )

    itineraries = router.plan(intent, db=raptor_db)
    assert len(itineraries) == 1
    assert itineraries[0].total_fare_inr == 1200.0  # 3A fare matched
    assert itineraries[0].legs[0].class_code == "3A"

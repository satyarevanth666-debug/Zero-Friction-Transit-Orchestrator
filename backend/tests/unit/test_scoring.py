"""Unit tests for Reliability Scoring and Balance Evaluation formulas (docs/SCORING.md)."""

import pytest

from app.planner.scoring import (
    compute_balance_score,
    compute_itinerary_reliability,
    compute_leg_reliability,
    compute_transfer_safety,
    is_late_night_hour,
)
from app.schemas.itinerary import Itinerary, Leg, TransferDetail


def test_leg_reliability_confirmed() -> None:
    leg = Leg(
        mode="rail",
        operator="Indian Railways",
        service_number="12785",
        service_name="Kacheguda Express",
        from_station_code="KCG",
        from_station_name="Kacheguda",
        to_station_code="MYS",
        to_station_name="Mysuru",
        departure_time="19:05",
        arrival_time="09:30",
        duration_minutes=865,
        availability_status="CNF",
    )
    assert compute_leg_reliability(leg) == 1.00


def test_leg_reliability_rac() -> None:
    leg = Leg(
        mode="rail",
        operator="Indian Railways",
        service_number="12785",
        service_name="Kacheguda Express",
        from_station_code="KCG",
        from_station_name="Kacheguda",
        to_station_code="MYS",
        to_station_name="Mysuru",
        departure_time="19:05",
        arrival_time="09:30",
        duration_minutes=865,
        availability_status="RAC",
    )
    assert compute_leg_reliability(leg) == 0.85


def test_leg_reliability_waitlist_probability() -> None:
    # 0.20 + 0.65 * 0.80 = 0.72
    leg = Leg(
        mode="rail",
        operator="Indian Railways",
        service_number="12785",
        service_name="Kacheguda Express",
        from_station_code="KCG",
        from_station_name="Kacheguda",
        to_station_code="MYS",
        to_station_name="Mysuru",
        departure_time="19:05",
        arrival_time="09:30",
        duration_minutes=865,
        availability_status="WL",
        confirmation_probability=0.80,
    )
    assert compute_leg_reliability(leg) == 0.72


def test_leg_reliability_timetable_defaults() -> None:
    leg_official = Leg(
        mode="rail",
        operator="Indian Railways",
        service_number="12785",
        service_name="Kacheguda Express",
        from_station_code="KCG",
        from_station_name="Kacheguda",
        to_station_code="MYS",
        to_station_name="Mysuru",
        departure_time="19:05",
        arrival_time="09:30",
        duration_minutes=865,
        truth_level="OFFICIAL_TIMETABLE",
    )
    assert compute_leg_reliability(leg_official) == 0.75

    leg_gtfs = Leg(
        mode="bus",
        operator="APSRTC",
        service_number="6201",
        service_name="Amaravathi",
        from_station_code="BZA",
        from_station_name="Vijayawada",
        to_station_code="HYB",
        to_station_name="Hyderabad",
        departure_time="06:00",
        arrival_time="11:30",
        duration_minutes=330,
        truth_level="COMMUNITY_GTFS",
    )
    assert compute_leg_reliability(leg_gtfs) == 0.70

    leg_unknown = Leg(
        mode="bus",
        operator="Private",
        service_number="000",
        service_name="Local Bus",
        from_station_code="A",
        from_station_name="A",
        to_station_code="B",
        to_station_name="B",
        departure_time="06:00",
        arrival_time="08:00",
        duration_minutes=120,
        truth_level="UNKNOWN",
    )
    assert compute_leg_reliability(leg_unknown) == 0.50


@pytest.mark.parametrize(
    "buf, is_cross, is_ln, expected_safety",
    [
        (15, False, False, 0.0),    # Infeasible (< 30 min)
        (35, False, False, 0.75),   # Tight (30 <= B < 45)
        (60, False, False, 1.00),   # Optimal (45 <= B <= 120)
        (150, False, False, 0.90),  # Fatigue (120 < B <= 240)
        (300, False, False, 0.70),  # Excessive (> 240)
        (60, False, True, 0.80),    # Optimal with late night (1.0 * 0.8)
        (50, True, False, 0.0),     # Cross-station with insufficient buffer (< 75 min)
        (90, True, False, 0.85),    # Cross-station optimal (1.0 * 0.85)
        (90, True, True, 0.68),     # Cross-station + late night (1.0 * 0.85 * 0.80 = 0.68)
    ],
)
def test_transfer_safety(buf: int, is_cross: bool, is_ln: bool, expected_safety: float) -> None:
    score = compute_transfer_safety(buf, is_cross_station=is_cross, is_late_night=is_ln)
    assert score == pytest.approx(expected_safety, abs=1e-3)


def test_is_late_night_hour() -> None:
    assert is_late_night_hour("23:15") is True
    assert is_late_night_hour("02:30") is True
    assert is_late_night_hour("04:20") is True
    assert is_late_night_hour("04:45") is False
    assert is_late_night_hour("14:30") is False


def test_composite_itinerary_reliability() -> None:
    # 2 legs: 1.00 (CNF) and 0.85 (RAC); 1 transfer: 1.00 (optimal 60m)
    # Total R = 1.00 * 0.85 * 1.00 = 0.85
    leg1 = Leg(
        mode="rail", operator="IR", service_number="1", service_name="A",
        from_station_code="A", from_station_name="A", to_station_code="B", to_station_name="B",
        departure_time="08:00", arrival_time="10:00", duration_minutes=120,
        reliability_score=1.00,
    )
    leg2 = Leg(
        mode="bus", operator="APSRTC", service_number="2", service_name="B",
        from_station_code="B", from_station_name="B", to_station_code="C", to_station_name="C",
        departure_time="11:00", arrival_time="13:00", duration_minutes=120,
        reliability_score=0.85,
    )
    trans = TransferDetail(
        from_station_code="B", to_station_code="B", buffer_minutes=60, safety_score=1.00
    )

    total_r = compute_itinerary_reliability([leg1, leg2], [trans])
    assert total_r == 0.85


def test_balance_score_formula() -> None:
    it = Itinerary(
        id="test1",
        legs=[],
        total_duration_minutes=300,
        departure_time="08:00",
        arrival_time="13:00",
        total_fare_inr=500.0,
        transfers_count=1,
        overall_reliability_score=0.90,
    )

    # Cost range: 300 to 700; Duration range: 200 to 400
    # C_norm = (500 - 300) / 400 = 0.50 -> 1 - 0.50 = 0.50
    # T_norm = (300 - 200) / 200 = 0.50 -> 1 - 0.50 = 0.50
    # transfers_penalty = 1 / 2 = 0.50
    # Score = 0.35*(0.50) + 0.35*(0.50) + 0.20*(0.90) - 0.10*(0.50)
    # Score = 0.175 + 0.175 + 0.180 - 0.050 = 0.4800
    score = compute_balance_score(it, min_cost=300.0, max_cost=700.0, min_time=200.0, max_time=400.0)
    assert score == pytest.approx(0.4800, abs=1e-4)

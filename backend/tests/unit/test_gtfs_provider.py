"""Unit tests for GTFS parsing, normalization, calendar bitmasks, and validation rules."""

import os
from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Calendar, CalendarException, DataSource, Service, StopTime
from app.providers.gtfs import (
    GtfsProvider,
    normalize_gtfs_time,
    parse_gtfs_date,
    time_to_seconds,
)


@pytest.fixture
def in_memory_db() -> Generator[Session, None, None]:


    """Create a fast, clean SQLite in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_gtfs_time_normalization_standard_and_over_24h() -> None:
    """Ensure times < 24:00:00 have day_offset 0 and times >= 24:00:00 have correct day_offset."""
    time_norm, day_offset = normalize_gtfs_time("14:30:00")
    assert time_norm == "14:30:00"
    assert day_offset == 0

    time_norm, day_offset = normalize_gtfs_time("25:30:00")
    assert time_norm == "01:30:00"
    assert day_offset == 1

    time_norm, day_offset = normalize_gtfs_time("28:15:45")
    assert time_norm == "04:15:45"
    assert day_offset == 1

    # Time over 48h threshold must raise ValueError
    with pytest.raises(ValueError, match="threshold"):
        normalize_gtfs_time("49:00:00")

    # Invalid string format must raise ValueError
    with pytest.raises(ValueError, match="Invalid time format"):
        normalize_gtfs_time("invalid-time")


def test_gtfs_date_parsing() -> None:
    """Ensure YYYYMMDD is correctly parsed into a datetime.date."""
    parsed = parse_gtfs_date("20261030")
    assert parsed == date(2026, 10, 30)


def test_time_to_seconds() -> None:
    """Test seconds conversion with day offsets."""
    assert time_to_seconds("01:00:00", 0) == 3600
    assert time_to_seconds("01:00:00", 1) == 86400 + 3600


def test_valid_gtfs_import_with_calendar_and_over_24h(in_memory_db: Session) -> None:
    """Verify that a valid GTFS zip imports services, stop times, and calendars correctly."""
    fixture_path = "data/fixtures/gtfs_rail.zip"
    assert os.path.exists(fixture_path), "Fixture data/fixtures/gtfs_rail.zip must exist"

    provider = GtfsProvider(
        provider_id="gtfs_rail_test",
        name="Test Rail GTFS",
        mode="rail",
        truth_level="COMMUNITY_GTFS",
        license_name="ODbL",
        file_path=fixture_path,
        rejects_csv_path="data/fixtures/test_rejects.csv",
    )

    result = provider.fetch_static(in_memory_db)

    assert result.services_imported == 3
    assert result.stop_times_imported == 9
    assert result.rejected_rows == 0
    assert result.is_expired is False
    assert result.checksum != ""

    # Verify overnight service with >24:00:00 time
    overnight_service = in_memory_db.query(Service).filter(
        Service.id == "gtfs_rail_test_TRIP_BZA_DMM_OVERNIGHT"
    ).first()
    assert overnight_service is not None
    assert len(overnight_service.stop_times) == 3

    # GTL stop should be arrive 01:30:00, day_offset 1
    gtl_stop = overnight_service.stop_times[1]
    assert gtl_stop.arrive == "01:30:00"
    assert gtl_stop.day_offset == 1

    # Verify calendar bitmask (CAL_DAILY has all 7 days = 127)
    cal = in_memory_db.query(Calendar).filter(
        Calendar.service_id == "gtfs_rail_test_TRIP_BZA_DMM_1"
    ).first()
    assert cal is not None
    assert cal.run_days == 127  # 1+2+4+8+16+32+64

    # Verify calendar exceptions
    exceptions = in_memory_db.query(CalendarException).filter(
        CalendarException.service_id == "gtfs_rail_test_TRIP_BZA_DMM_1"
    ).all()
    assert len(exceptions) == 1
    assert exceptions[0].exception_type == 2  # Removed service on that date

    # Verify data source recorded license & checksum
    ds = in_memory_db.query(DataSource).filter(DataSource.id == "gtfs_rail_test").first()
    assert ds is not None
    assert ds.license == "ODbL"
    assert ds.checksum == result.checksum


def test_idempotent_gtfs_import(in_memory_db: Session) -> None:
    """Verify that importing the exact same feed twice is strictly idempotent."""
    fixture_path = "data/fixtures/gtfs_rail.zip"
    provider = GtfsProvider(
        provider_id="gtfs_rail_idempotent",
        name="Idempotent Test",
        mode="rail",
        truth_level="COMMUNITY_GTFS",
        license_name="ODbL",
        file_path=fixture_path,
        rejects_csv_path="data/fixtures/test_rejects.csv",
    )

    # First import
    res1 = provider.fetch_static(in_memory_db)
    service_count_1 = in_memory_db.query(Service).filter(Service.source_id == "gtfs_rail_idempotent").count()
    stop_count_1 = in_memory_db.query(StopTime).join(Service).filter(Service.source_id == "gtfs_rail_idempotent").count()

    # Second import of same feed
    res2 = provider.fetch_static(in_memory_db)
    service_count_2 = in_memory_db.query(Service).filter(Service.source_id == "gtfs_rail_idempotent").count()
    stop_count_2 = in_memory_db.query(StopTime).join(Service).filter(Service.source_id == "gtfs_rail_idempotent").count()

    assert service_count_1 == service_count_2 == 3
    assert stop_count_1 == stop_count_2 == 9
    assert res1.services_imported == res2.services_imported


def test_expired_calendar_flagged(in_memory_db: Session) -> None:
    """Verify that feeds with expired calendar are flagged with is_expired=True."""
    fixture_path = "data/fixtures/expired_gtfs.zip"
    provider = GtfsProvider(
        provider_id="gtfs_expired",
        name="Expired Rail Feed",
        mode="rail",
        truth_level="COMMUNITY_GTFS",
        license_name="ODbL",
        file_path=fixture_path,
        rejects_csv_path="data/fixtures/test_rejects.csv",
    )

    result = provider.fetch_static(in_memory_db)
    assert result.is_expired is True
    assert result.valid_to == date(2023, 12, 31)


def test_corrupted_gtfs_bad_rows_rejected_and_logged(in_memory_db: Session) -> None:
    """Verify that orphan stops, negative durations, and >48h times are rejected and logged to rejects.csv."""
    fixture_path = "data/fixtures/corrupted_gtfs.zip"
    rejects_path = "data/fixtures/corrupted_rejects.csv"
    if os.path.exists(rejects_path):
        os.remove(rejects_path)

    provider = GtfsProvider(
        provider_id="gtfs_corrupted",
        name="Corrupted Rail Feed",
        mode="rail",
        truth_level="COMMUNITY_GTFS",
        license_name="ODbL",
        file_path=fixture_path,
        rejects_csv_path=rejects_path,
    )

    result = provider.fetch_static(in_memory_db)
    assert result.rejected_rows > 0

    # Ensure rejects.csv exists and contains error descriptions
    assert os.path.exists(rejects_path)
    with open(rejects_path, encoding="utf-8") as f:
        content = f.read()
        assert "timestamp,provider_id,row_type" in content
        assert "gtfs_corrupted" in content

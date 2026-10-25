"""Integration tests for database seeding and provider registry."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import City, Service, Station, TransferEdge
from app.db.seed import seed_database
from app.providers.gtfs import GtfsProvider
from app.providers.registry import registry


@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_seed_database_populates_nodes(test_db: Session) -> None:

    """Verify seed populates baseline cities, stations, and transfer edges."""
    from app.db.session import engine
    # Initialize schema on engine
    Base.metadata.create_all(engine)

    seed_database()

    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        cities_count = db.query(City).count()
        stations_count = db.query(Station).count()
        transfers_count = db.query(TransferEdge).count()

        assert cities_count >= 10
        assert stations_count >= 14
        assert transfers_count >= 8

        # Check key stations exist
        bza = db.query(Station).filter(Station.code == "BZA").first()
        dmm = db.query(Station).filter(Station.code == "DMM").first()
        assert bza is not None
        assert dmm is not None
    finally:
        db.close()


def test_provider_registry_health_checks() -> None:
    """Verify provider registry lists enabled providers and health status."""
    providers = registry.list_all()
    assert len(providers) >= 4

    health_reports = registry.health_check_all()
    assert len(health_reports) >= 4

    provider_ids = [h["provider_id"] for h in health_reports]
    assert "user_provided" in provider_ids
    assert "datameet_rail" in provider_ids
    assert "fares_estimated" in provider_ids


def test_import_both_rail_and_bus_feeds(test_db: Session) -> None:
    """Verify both rail and APSRTC bus feeds can be ingested together."""

    rail_provider = GtfsProvider(
        provider_id="rail_combined",
        name="Rail Combined",
        mode="rail",
        truth_level="OFFICIAL_TIMETABLE",
        license_name="Open Data",
        file_path="data/fixtures/gtfs_rail.zip",
        rejects_csv_path="data/fixtures/test_rejects.csv",
    )
    bus_provider = GtfsProvider(
        provider_id="bus_combined",
        name="Bus Combined",
        mode="bus",
        truth_level="COMMUNITY_GTFS",
        license_name="CC-BY",
        file_path="data/fixtures/gtfs_bus_apsrtc.zip",
        rejects_csv_path="data/fixtures/test_rejects.csv",
    )

    rail_res = rail_provider.fetch_static(test_db)
    bus_res = bus_provider.fetch_static(test_db)

    assert rail_res.services_imported == 3
    assert bus_res.services_imported == 2

    total_services = test_db.query(Service).count()
    assert total_services == 5

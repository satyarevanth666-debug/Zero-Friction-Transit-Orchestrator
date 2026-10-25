"""Database seed script for baseline geography and transfer edges."""

import structlog

from app.db.models import Alias, City, Station, TransferEdge
from app.db.session import SessionLocal, init_db

logger = structlog.get_logger("zero-friction-transit")


def seed_database() -> None:
    """Populate baseline cities, stations, aliases, and transfer connections."""
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(City).first():
            logger.info("Database already seeded with geographic data.")
            return

        logger.info("Seeding database with baseline geography...")

        # 1. Cities
        cities_data = [
            City(id=1, name="Vijayawada", state="Andhra Pradesh", district="NTR", lat=16.5062, lon=80.6480),
            City(id=2, name="Dharmavaram", state="Andhra Pradesh", district="Sri Sathya Sai", lat=14.4137, lon=77.7281),
            City(id=3, name="Amaravati", state="Andhra Pradesh", district="Guntur", lat=16.5131, lon=80.5165),
            City(id=4, name="Guntur", state="Andhra Pradesh", district="Guntur", lat=16.3067, lon=80.4365),
            City(id=5, name="Hindupur", state="Andhra Pradesh", district="Sri Sathya Sai", lat=13.8284, lon=77.4919),
            City(id=6, name="Anantapur", state="Andhra Pradesh", district="Anantapur", lat=14.6819, lon=77.6006),
            City(id=7, name="Hyderabad", state="Telangana", district="Hyderabad", lat=17.3850, lon=78.4867),
            City(id=8, name="Tirupati", state="Andhra Pradesh", district="Tirupati", lat=13.6288, lon=79.4192),
            City(id=9, name="Bengaluru", state="Karnataka", district="Bengaluru Urban", lat=12.9716, lon=77.5946),
            City(id=10, name="Chennai", state="Tamil Nadu", district="Chennai", lat=13.0827, lon=80.2707),
        ]
        db.add_all(cities_data)
        db.flush()

        # 2. Stations
        stations_data = [
            Station(id=1, code="BZA", name="Vijayawada Junction", type="rail", city_id=1, lat=16.5186, lon=80.6200),
            Station(id=2, code="BZA_BUS", name="Pandit Nehru Bus Station (PNBS)", type="bus_stand", city_id=1, lat=16.5085, lon=80.6174),
            Station(id=3, code="DMM", name="Dharmavaram Junction", type="rail", city_id=2, lat=14.4172, lon=77.7180),
            Station(id=4, code="DMM_BUS", name="Dharmavaram APSRTC Bus Stand", type="bus_stand", city_id=2, lat=14.4110, lon=77.7240),
            Station(id=5, code="GNT", name="Guntur Junction", type="rail", city_id=4, lat=16.2974, lon=80.4438),
            Station(id=6, code="HUP", name="Hindupur Railway Station", type="rail", city_id=5, lat=13.8299, lon=77.4950),
            Station(id=7, code="HUP_BUS", name="Hindupur Bus Stand", type="bus_stand", city_id=5, lat=13.8260, lon=77.4910),
            Station(id=8, code="ATP", name="Anantapur Railway Station", type="rail", city_id=6, lat=14.6853, lon=77.6009),
            Station(id=9, code="ATP_BUS", name="Anantapur Bus Station", type="bus_stand", city_id=6, lat=14.6780, lon=77.5950),
            Station(id=10, code="HYB", name="Hyderabad Deccan (Nampally)", type="rail", city_id=7, lat=17.3920, lon=78.4680),
            Station(id=11, code="SC", name="Secunderabad Junction", type="rail", city_id=7, lat=17.4339, lon=78.5017),
            Station(id=12, code="TPTY", name="Tirupati Main", type="rail", city_id=8, lat=13.6288, lon=79.4210),
            Station(id=13, code="SBC", name="KSR Bengaluru City Junction", type="rail", city_id=9, lat=12.9784, lon=77.5694),
            Station(id=14, code="MAS", name="Chennai Central", type="rail", city_id=10, lat=13.0827, lon=80.2757),
            Station(id=15, code="VGA", name="Vijayawada International Airport", type="airport", city_id=1, lat=16.5304, lon=80.7968),
            Station(id=16, code="HYD_AIR", name="Rajiv Gandhi International Airport", type="airport", city_id=7, lat=17.2403, lon=78.4294),
        ]
        db.add_all(stations_data)
        db.flush()

        # 3. Aliases (English, Telugu, Hindi)
        aliases_data = [
            Alias(alias="Bezawada", city_id=1, lang="en"),
            Alias(alias="విజయవాడ", city_id=1, lang="te"),
            Alias(alias="विजयवाड़ा", city_id=1, lang="hi"),
            Alias(alias="ధర్మవరం", city_id=2, lang="te"),
            Alias(alias="धर्मवरम", city_id=2, lang="hi"),
            Alias(alias="అమరావతి", city_id=3, lang="te"),
            Alias(alias="అనంతపురం", city_id=6, lang="te"),
            Alias(alias="Secunderabad", city_id=7, lang="en"),
            Alias(alias="సికింద్రాబాద్", city_id=7, lang="te"),
            Alias(alias="హైదరాబాద్", city_id=7, lang="te"),
            Alias(alias="हैदराबाद", city_id=7, lang="hi"),
            Alias(alias="తిరుపతి", city_id=8, lang="te"),
            Alias(alias="Bangalore", city_id=9, lang="en"),
            Alias(alias="బెంగళూరు", city_id=9, lang="te"),
            Alias(alias="मद्रास", city_id=10, lang="hi"),
        ]
        db.add_all(aliases_data)

        # 4. Transfer Edges (Station-to-Station connections with walk/auto durations)
        transfer_data = [
            # Vijayawada Junction <-> PNBS Bus Stand (1.8 km, ~15 min auto/walk)
            TransferEdge(from_station_code="BZA", to_station_code="BZA_BUS", minutes=15, cost_inr=50, notes="Auto-rickshaw / city shuttle"),
            TransferEdge(from_station_code="BZA_BUS", to_station_code="BZA", minutes=15, cost_inr=50, notes="Auto-rickshaw / city shuttle"),
            # Dharmavaram Junction <-> Dharmavaram Bus Stand (1.2 km, ~12 min)
            TransferEdge(from_station_code="DMM", to_station_code="DMM_BUS", minutes=12, cost_inr=30, notes="Auto or short walk"),
            TransferEdge(from_station_code="DMM_BUS", to_station_code="DMM", minutes=12, cost_inr=30, notes="Auto or short walk"),
            # Anantapur Railway <-> Anantapur Bus Stand (1.5 km, ~15 min)
            TransferEdge(from_station_code="ATP", to_station_code="ATP_BUS", minutes=15, cost_inr=40, notes="Auto transfer"),
            TransferEdge(from_station_code="ATP_BUS", to_station_code="ATP", minutes=15, cost_inr=40, notes="Auto transfer"),
            # Hindupur Railway <-> Hindupur Bus Stand (0.8 km, ~10 min)
            TransferEdge(from_station_code="HUP", to_station_code="HUP_BUS", minutes=10, cost_inr=30, notes="Walk or auto"),
            TransferEdge(from_station_code="HUP_BUS", to_station_code="HUP", minutes=10, cost_inr=30, notes="Walk or auto"),
            # Secunderabad <-> Hyderabad Deccan (Metro / auto: ~35 min)
            TransferEdge(from_station_code="SC", to_station_code="HYB", minutes=35, cost_inr=40, notes="Hyderabad Metro Red Line connection"),
            TransferEdge(from_station_code="HYB", to_station_code="SC", minutes=35, cost_inr=40, notes="Hyderabad Metro Red Line connection"),
        ]
        db.add_all(transfer_data)

        db.commit()
        logger.info("Database seeding successfully completed.")
    except Exception as e:
        db.rollback()
        logger.error("Database seeding failed", error=str(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

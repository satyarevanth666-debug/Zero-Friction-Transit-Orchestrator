"""Import script for official Railway Board 'Trains at a Glance' timetable."""

import structlog

from app.db.session import SessionLocal, init_db
from app.providers.official_rail import OfficialRailTimetableProvider

logger = structlog.get_logger("zero-friction-transit")


def import_official_rail() -> None:
    init_db()
    db = SessionLocal()
    try:
        provider = OfficialRailTimetableProvider()
        result = provider.fetch_static(db)
        if result.errors:
            for err in result.errors:
                logger.info("Official rail status", message=err)
    finally:
        db.close()


if __name__ == "__main__":
    import_official_rail()

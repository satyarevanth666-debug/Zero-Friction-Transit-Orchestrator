"""Import script for static GTFS transit archives."""

import structlog

from app.db.session import SessionLocal, init_db
from app.providers.gtfs import GtfsProvider
from app.providers.registry import registry

logger = structlog.get_logger("zero-friction-transit")


def import_all_gtfs() -> None:
    """Find all configured GtfsProviders and execute static timetable imports."""
    init_db()
    db = SessionLocal()

    try:
        gtfs_providers = [p for p in registry.list_all() if isinstance(p, GtfsProvider)]
        logger.info("Starting GTFS import pipeline", count=len(gtfs_providers))

        for provider in gtfs_providers:
            if not provider.enabled:
                logger.info("Skipping disabled provider", provider=provider.provider_id)
                continue

            logger.info("Importing GTFS feed", provider=provider.provider_id, path=provider.file_path)
            res = provider.fetch_static(db)
            logger.info(
                "Feed imported",
                provider=provider.provider_id,
                services=res.services_imported,
                stop_times=res.stop_times_imported,
                rejected=res.rejected_rows,
                expired=res.is_expired,
            )

    finally:
        db.close()


if __name__ == "__main__":
    import_all_gtfs()

"""Nightly / startup refresh orchestrator for all registered transit providers."""

import structlog

from app.db.session import SessionLocal, init_db
from app.providers.registry import registry

logger = structlog.get_logger("zero-friction-transit")


def refresh_all() -> None:
    """Execute change-detection refresh across all active transit providers."""
    init_db()
    db = SessionLocal()
    try:
        logger.info("Executing comprehensive transit provider refresh...")
        for provider in registry.list_active():
            logger.info("Refreshing provider", provider_id=provider.provider_id)
            res = provider.fetch_static(db)
            if res.errors:
                logger.error("Provider refresh errors", provider=provider.provider_id, errors=res.errors)
        logger.info("Comprehensive provider refresh completed.")
    finally:
        db.close()


if __name__ == "__main__":
    refresh_all()

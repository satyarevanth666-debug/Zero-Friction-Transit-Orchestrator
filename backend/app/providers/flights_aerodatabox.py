"""AeroDataBox Flight API adapter for airport movements and flight schedules."""

from typing import Any

from sqlalchemy.orm import Session

from app.providers.base import ImportResult, TransitProvider


class FlightAeroDataBoxProvider(TransitProvider):
    """Adapter for AeroDataBox flight schedules."""

    def __init__(
        self,
        provider_id: str = "flights_aerodatabox",
        name: str = "AeroDataBox Flight Movements",
        truth_level: str = "LIVE_API",
        license_name: str = "RapidAPI Free Tier",
        api_key: str | None = None,
        enabled: bool = False,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            name=name,
            mode="flight",
            truth_level=truth_level,
            license_name=license_name,
            enabled=enabled,
        )
        self.api_key = api_key

    def fetch_static(self, db: Session, file_path: str | None = None) -> ImportResult:
        return ImportResult(provider_id=self.provider_id)

    def fetch_dynamic(self, query: Any) -> list[Any] | None:
        return None

    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "mode": self.mode,
            "truth_level": self.truth_level,
            "status": "ready" if (self.enabled and self.api_key) else "disabled",
        }

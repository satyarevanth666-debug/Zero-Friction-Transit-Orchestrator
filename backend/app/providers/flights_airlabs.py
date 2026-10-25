"""AirLabs Flight API adapter for flight schedules and status."""

from typing import Any

from sqlalchemy.orm import Session

from app.providers.base import ImportResult, TransitProvider


class FlightAirLabsProvider(TransitProvider):
    """Adapter for AirLabs flight schedules and live status."""

    def __init__(
        self,
        provider_id: str = "flights_airlabs",
        name: str = "AirLabs Aviation Schedules",
        truth_level: str = "LIVE_API",
        license_name: str = "Developer Tier License",
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
        if not self.enabled or not self.api_key:
            return None
        return []

    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "mode": self.mode,
            "truth_level": self.truth_level,
            "has_api_key": bool(self.api_key),
            "status": "ready" if (self.enabled and self.api_key) else "disabled",
        }

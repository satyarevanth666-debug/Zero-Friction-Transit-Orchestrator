"""DataMeet Rail Provider (CC0 archived stations fallback)."""

from typing import Any

from sqlalchemy.orm import Session

from app.providers.base import ImportResult, TransitProvider


class DatameetRailProvider(TransitProvider):
    """Fallback provider for station names and coordinates (DataMeet CC0)."""

    def __init__(
        self,
        provider_id: str = "datameet_rail",
        name: str = "DataMeet Indian Railways Geospatial Archive",
        truth_level: str = "OFFICIAL_TIMETABLE",
        license_name: str = "CC0 1.0 Universal",
        enabled: bool = True,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            name=name,
            mode="rail",
            truth_level=truth_level,
            license_name=license_name,
            enabled=enabled,
        )
        self.possibly_outdated = True

    def fetch_static(self, db: Session, file_path: str | None = None) -> ImportResult:
        result = ImportResult(provider_id=self.provider_id)
        return result

    def fetch_dynamic(self, query: Any) -> list[Any] | None:
        return None

    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "mode": self.mode,
            "truth_level": self.truth_level,
            "license": self.license,
            "possibly_outdated": self.possibly_outdated,
            "status": "ready",
        }

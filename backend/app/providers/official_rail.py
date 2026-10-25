"""Railway Board 'Trains at a Glance' official timetable importer."""

import os
from typing import Any

from sqlalchemy.orm import Session

from app.providers.base import ImportResult, TransitProvider


class OfficialRailTimetableProvider(TransitProvider):
    """Importer for official Railway Board 'Trains at a Glance' timetable data."""

    def __init__(
        self,
        provider_id: str = "official_rail",
        name: str = "Railway Board 'Trains at a Glance'",
        truth_level: str = "OFFICIAL_TIMETABLE",
        license_name: str = "Government of India / Open Access",
        file_path: str | None = "data/raw/trains_at_a_glance.csv",
        enabled: bool = False,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            name=name,
            mode="rail",
            truth_level=truth_level,
            license_name=license_name,
            enabled=enabled,
        )
        self.file_path = file_path

    def fetch_static(self, db: Session, file_path: str | None = None) -> ImportResult:
        result = ImportResult(provider_id=self.provider_id)
        target = file_path or self.file_path
        if not target or not os.path.exists(target):
            result.errors.append(f"Official timetable file not found at {target}. Awaiting user file.")
            return result
        # Parsing implementation when user places official file
        return result

    def fetch_dynamic(self, query: Any) -> list[Any] | None:
        return None

    def health(self) -> dict[str, Any]:
        has_file = os.path.exists(self.file_path) if self.file_path else False
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "mode": self.mode,
            "truth_level": self.truth_level,
            "enabled": self.enabled,
            "status": "ready" if has_file else "awaiting_source_file",
        }

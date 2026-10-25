"""Base classes and interfaces for transit data providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session


@dataclass
class ImportResult:
    """Telemetry and outcome of a static transit data import."""
    provider_id: str
    services_imported: int = 0
    stop_times_imported: int = 0
    calendars_imported: int = 0
    fares_imported: int = 0
    rejected_rows: int = 0
    valid_from: date | None = None
    valid_to: date | None = None
    checksum: str = ""
    is_expired: bool = False
    errors: list[str] = field(default_factory=list)


class TransitProvider(ABC):
    """Abstract interface implemented by all transit data sources."""

    def __init__(
        self,
        provider_id: str,
        name: str,
        mode: str,
        truth_level: str,
        license_name: str,
        enabled: bool = True,
    ) -> None:
        self.provider_id = provider_id
        self.name = name
        self.mode = mode
        self.truth_level = truth_level
        self.license = license_name
        self.enabled = enabled

    @abstractmethod
    def fetch_static(self, db: Session, file_path: str | None = None) -> ImportResult:
        """Import static schedules, routes, stops, and calendars into the database."""

    @abstractmethod
    def fetch_dynamic(self, query: Any) -> list[Any] | None:
        """Fetch live dynamic updates, delays, or seat availability."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Report operational health status and coverage metadata."""

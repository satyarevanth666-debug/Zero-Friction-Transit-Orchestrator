"""Session-scoped user provided availability and fare data."""

from typing import Any

from sqlalchemy.orm import Session

from app.providers.base import ImportResult, TransitProvider


class UserProvidedProvider(TransitProvider):
    """Handles transient, session-scoped availability and fare overrides reported by the user."""

    def __init__(
        self,
        provider_id: str = "user_provided",
        name: str = "User Reported Availability & Fares",
        truth_level: str = "USER_PROVIDED",
        license_name: str = "Session User Contribution",
        enabled: bool = True,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            name=name,
            mode="all",
            truth_level=truth_level,
            license_name=license_name,
            enabled=enabled,
        )

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
            "status": "ready",
        }

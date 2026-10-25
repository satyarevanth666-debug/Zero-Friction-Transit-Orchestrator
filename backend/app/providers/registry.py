"""Provider registry loading providers.yaml and orchestrating active data sources."""

import os
from typing import Any

import yaml

from app.config import settings
from app.providers.base import TransitProvider
from app.providers.datameet import DatameetRailProvider
from app.providers.fares_estimated import EstimatedFareProvider
from app.providers.flights_airlabs import FlightAirLabsProvider
from app.providers.gtfs import GtfsProvider
from app.providers.official_rail import OfficialRailTimetableProvider
from app.providers.rail_availability import RailAvailabilityProvider
from app.providers.user_provided import UserProvidedProvider


class ProviderRegistry:
    """Central registry and life-cycle manager for all transit providers."""

    def __init__(self, config_path: str = "data/providers.yaml") -> None:
        self.config_path = config_path
        self._providers: dict[str, TransitProvider] = {}
        self.load_providers()

    def load_providers(self) -> None:
        """Parse providers.yaml and instantiate providers with active feature flags."""
        from app.config import resolve_data_path
        self._providers.clear()

        # Always register standard system providers
        self.register(UserProvidedProvider())
        self.register(DatameetRailProvider())
        self.register(EstimatedFareProvider(yaml_path="data/fares.yaml"))

        actual_config = resolve_data_path(self.config_path)
        if not os.path.exists(actual_config):
            return

        try:
            with open(actual_config, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                providers_list = data.get("providers", [])

            for p_cfg in providers_list:
                p_id = p_cfg.get("id")
                source_type = p_cfg.get("source_type")
                name = p_cfg.get("name", p_id)
                mode = p_cfg.get("mode", "rail")
                truth_level = p_cfg.get("truth_level", "OFFICIAL_TIMETABLE")
                license_name = p_cfg.get("license", "Open Data")
                file_path = p_cfg.get("file_path")
                if file_path:
                    file_path = resolve_data_path(file_path)
                enabled = p_cfg.get("enabled", True)

                # Feature flag overrides from environment
                if p_id == "rail_availability":
                    enabled = settings.ENABLE_THIRD_PARTY_RAIL
                elif p_id == "official_rail" and not (file_path and os.path.exists(file_path)):
                    enabled = False

                provider: TransitProvider
                if source_type == "gtfs_zip":
                    provider = GtfsProvider(
                        provider_id=p_id,
                        name=name,
                        mode=mode,
                        truth_level=truth_level,
                        license_name=license_name,
                        file_path=file_path,
                        enabled=enabled,
                    )
                    self.register(provider)
                elif source_type == "official_timetable":
                    provider = OfficialRailTimetableProvider(
                        provider_id=p_id,
                        name=name,
                        truth_level=truth_level,
                        license_name=license_name,
                        file_path=file_path,
                        enabled=enabled,
                    )
                    self.register(provider)
                elif source_type == "flight_schedule":
                    provider = FlightAirLabsProvider(
                        provider_id=p_id,
                        name=name,
                        truth_level=truth_level,
                        license_name=license_name,
                        api_key=settings.FLIGHT_API_KEY,
                        enabled=enabled,
                    )
                    self.register(provider)
                elif source_type == "rail_api":
                    provider = RailAvailabilityProvider(
                        provider_id=p_id,
                        name=name,
                        truth_level=truth_level,
                        license_name=license_name,
                        api_key=settings.RAIL_API_KEY,
                        enabled=enabled,
                    )
                    self.register(provider)

        except (yaml.YAMLError, OSError, ValueError) as err:
            import structlog
            structlog.get_logger("zero-friction-transit").warning("Failed to load providers config", error=str(err))


    def register(self, provider: TransitProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> TransitProvider | None:
        """Retrieve a registered provider by its unique identifier."""
        return self._providers.get(provider_id)

    def list_all(self) -> list[TransitProvider]:
        """Return all registered providers."""
        return list(self._providers.values())

    def list_active(self) -> list[TransitProvider]:
        """Return all currently active and enabled providers."""
        return [p for p in self._providers.values() if p.enabled]

    def health_check_all(self) -> list[dict[str, Any]]:
        """Run health checks across all registered providers."""
        return [p.health() for p in self._providers.values()]


# Global registry singleton
registry = ProviderRegistry()

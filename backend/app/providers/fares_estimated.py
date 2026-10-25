"""Distance-based telescopic fare estimation provider with citations."""

import math
import os
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.providers.base import ImportResult, TransitProvider


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0  # Earth's radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class EstimatedFareProvider(TransitProvider):
    """Computes transparent, estimated telescopic fares based on published rules."""

    def __init__(
        self,
        provider_id: str = "fares_estimated",
        name: str = "Indian Railways & Roadways Telescopic Fares",
        truth_level: str = "ESTIMATED",
        license_name: str = "Published Coaching Tariff Rules",
        yaml_path: str = "data/fares.yaml",
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
        self.yaml_path = yaml_path
        self._rules: dict[str, Any] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Load fare slab rules from fares.yaml."""
        from app.config import resolve_data_path
        actual_path = resolve_data_path(self.yaml_path)
        if os.path.exists(actual_path):
            try:
                with open(actual_path, encoding="utf-8") as f:
                    self._rules = yaml.safe_load(f) or {}
            except (yaml.YAMLError, OSError):
                self._rules = {}



    def calculate_fare(
        self,
        mode: str,
        class_code: str,
        distance_km: float,
        from_station: str | None = None,
        to_station: str | None = None,
    ) -> float | None:
        """
        Compute estimated fare using published slabs. Returns None if uncomputable.
        """
        # 1. Check fixed corridor overrides first
        overrides = self._rules.get("fixed_corridor_overrides", [])
        if from_station and to_station:
            for item in overrides:
                if (
                    item.get("origin") == from_station
                    and item.get("destination") == to_station
                    and item.get("class", "").upper() == class_code.upper()
                ):
                    return float(item.get("amount", 0))

        # 2. Telescopic Rail Fares
        class_key_map = {
            "SL": "sleeper",
            "3A": "third_ac",
            "2A": "second_ac",
            "1A": "first_ac",
            "2S": "second_seating",
            "CC": "chair_car",
        }
        if mode == "rail":
            rail_rules = self._rules.get("rail_fares", {})
            mapped_key = class_key_map.get(class_code.upper(), class_code.lower())
            if mapped_key in rail_rules:
                rule = rail_rules[mapped_key]
                base_fare = float(rule.get("base_fare", 0))
                rate_per_km = float(rule.get("rate_per_km", 0))
                min_dist = float(rule.get("min_distance", 0))
                effective_dist = max(distance_km, min_dist)
                return round(base_fare + (effective_dist * rate_per_km))

        # 3. Telescopic Bus Fares
        bus_key_map = {
            "EXP": "express",
            "EXPRESS": "express",
            "UD": "ultra_deluxe",
            "ULTRA_DELUXE": "ultra_deluxe",
            "SL": "super_luxury",
            "SUPER_LUXURY": "super_luxury",
            "GARUDA": "garuda_ac",
            "AC": "garuda_ac",
            "AMARAVATHI": "amaravathi_multi_axle",
        }
        if mode == "bus":
            bus_rules = self._rules.get("bus_fares", {})
            mapped_bus = bus_key_map.get(class_code.upper(), class_code.lower())
            if mapped_bus in bus_rules:
                rule = bus_rules[mapped_bus]
                base_fare = float(rule.get("base_fare", 0))
                rate_per_km = float(rule.get("rate_per_km", 0))
                return round(base_fare + (distance_km * rate_per_km))

        # Unknown / unconfigured rule -> return None (honest NULL)
        return None

    def fetch_static(self, db: Session, file_path: str | None = None) -> ImportResult:
        """Populate database with station-pair fare estimates for known routes."""
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
            "citation": self._rules.get("citation", "Published Tariff"),
            "status": "ready" if self._rules else "no_rules_loaded",
        }

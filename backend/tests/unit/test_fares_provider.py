"""Unit tests for distance-based estimated fare calculations and NULL safety."""

from app.providers.fares_estimated import EstimatedFareProvider, haversine_distance_km


def test_haversine_distance() -> None:
    """Check distance calculation between Vijayawada (16.5186, 80.6200) and Dharmavaram (14.4172, 77.7180)."""
    dist = haversine_distance_km(16.5186, 80.6200, 14.4172, 77.7180)
    # Approx 390-405 km as crow flies
    assert 380 <= dist <= 420


def test_estimated_fare_fixed_corridor_override() -> None:
    """Ensure verified fixed corridor overrides take precedence."""
    provider = EstimatedFareProvider(yaml_path="data/fares.yaml")

    # BZA -> DMM Sleeper fixed override is 320
    fare = provider.calculate_fare(
        mode="rail", class_code="SL", distance_km=420, from_station="BZA", to_station="DMM"
    )
    assert fare == 320.0

    # 3A fixed override is 860
    fare_3a = provider.calculate_fare(
        mode="rail", class_code="3A", distance_km=420, from_station="BZA", to_station="DMM"
    )
    assert fare_3a == 860.0


def test_estimated_fare_telescopic_calculation() -> None:
    """Ensure telescopic formula calculates base + (km * rate)."""
    provider = EstimatedFareProvider(yaml_path="data/fares.yaml")

    # Sleeper: base 120, rate 0.38/km, min 100km
    # For 200 km: 120 + 200 * 0.38 = 196
    fare_sl = provider.calculate_fare(mode="rail", class_code="SL", distance_km=200)
    assert fare_sl == 196.0

    # Bus Super Luxury: base 65, rate 1.65/km
    # For 100 km: 65 + 100 * 1.65 = 230
    fare_bus = provider.calculate_fare(mode="bus", class_code="super_luxury", distance_km=100)
    assert fare_bus == 230.0


def test_estimated_fare_unknown_returns_none() -> None:
    """Unknown mode or unconfigured class MUST return None (NULL-safety)."""
    provider = EstimatedFareProvider(yaml_path="data/fares.yaml")

    unknown_fare = provider.calculate_fare(mode="unknown_mode", class_code="XYZ", distance_km=150)
    assert unknown_fare is None

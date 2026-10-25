"""Reliability scoring and multi-criteria balance evaluation for transit itineraries.

Implements formulas defined in docs/SCORING.md:
- Leg reliability: CNF (1.00), RAC (0.85), WL (scaled), Timetable (0.75/0.70), Unknown (0.50).
- Transfer safety: Buffer windows, late-night layover penalty, and cross-station transfer penalty.
- Composite reliability score R = Product(LegReliability) * Product(TransferSafety).
- Balance score formula with configurable weights.
"""

from collections.abc import Sequence

from app.schemas.itinerary import Itinerary, Leg, TransferDetail


def compute_leg_reliability(leg: Leg) -> float:
    """Calculate reliability score for an individual journey leg."""
    status = (leg.availability_status or "").upper()

    if status == "CNF":
        return 1.00
    if status == "RAC":
        return 0.85
    if status == "WL":
        p_confirm = leg.confirmation_probability
        if p_confirm is None:
            # Monotonic heuristic fallback if ML model is unavailable
            pos = leg.waitlist_position or 30
            p_confirm = max(0.0, 1.0 - (pos / 100.0))
        return round(0.20 + (0.65 * p_confirm), 3)

    # Truth level defaults when availability status is unreserved or not reported
    truth = (leg.truth_level or "").upper()
    if truth == "OFFICIAL_TIMETABLE":
        return 0.75
    if truth == "COMMUNITY_GTFS":
        return 0.70

    return 0.50


def compute_transfer_safety(
    buffer_minutes: int,
    is_cross_station: bool = False,
    is_late_night: bool = False,
) -> float:
    """
    Compute transfer safety score based on buffer duration and risk factors.
    Returns 0.0 if transfer buffer is strictly infeasible.
    """
    # Cross-station transfers require at least 75 minutes buffer
    if is_cross_station and buffer_minutes < 75:
        return 0.0

    # Same-station minimum buffer is 30 minutes
    if buffer_minutes < 30:
        return 0.0

    # Base buffer safety score
    if buffer_minutes < 45:
        score = 0.75
    elif buffer_minutes <= 120:
        score = 1.00
    elif buffer_minutes <= 240:
        score = 0.90
    else:
        score = 0.70

    # Late-night transfer penalty (between 23:00 and 04:30)
    if is_late_night:
        score *= 0.80

    # Cross-station transfer penalty factor
    if is_cross_station:
        score *= 0.85

    return round(score, 3)


def is_late_night_hour(time_str: str) -> bool:
    """Check if time falls in late-night layover window (23:00 to 04:30)."""
    try:
        parts = time_str.split(":")
        hr = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        total_min = hr * 60 + minute
        # 23:00 = 1380 min; 04:30 = 270 min
        return total_min >= 1380 or total_min <= 270
    except (ValueError, IndexError):
        return False


def compute_itinerary_reliability(
    legs: Sequence[Leg],
    transfers: Sequence[TransferDetail],
) -> float:
    """
    Compute total itinerary reliability score R:
    R = Product(LegReliability) * Product(TransferSafety).
    """
    if not legs:
        return 0.0

    score = 1.0

    for leg in legs:
        score *= leg.reliability_score

    for transfer in transfers:
        score *= transfer.safety_score

    return round(max(0.0, min(1.0, score)), 3)


def compute_balance_score(
    itinerary: Itinerary,
    min_cost: float,
    max_cost: float,
    min_time: float,
    max_time: float,
    w_cost: float = 0.35,
    w_time: float = 0.35,
    w_rel: float = 0.20,
    w_transfers: float = 0.10,
) -> float:
    """
    Compute Best Balance composite score for Pareto ranking.
    Score = w_cost*(1 - C_norm) + w_time*(1 - T_norm) + w_rel*R - w_transfers*(N_transfers/2).
    """
    # Normalize cost
    if itinerary.total_fare_inr is not None:
        if max_cost > min_cost:
            c_norm = (itinerary.total_fare_inr - min_cost) / (max_cost - min_cost)
        else:
            c_norm = 0.0
    else:
        # Honest neutral cost assumption for unverified fares
        c_norm = 0.50

    # Normalize travel duration
    if max_time > min_time:
        t_norm = (itinerary.total_duration_minutes - min_time) / (max_time - min_time)
    else:
        t_norm = 0.0

    r = itinerary.overall_reliability_score
    transfer_penalty = min(itinerary.transfers_count / 2.0, 1.0)

    score = (
        (w_cost * (1.0 - c_norm))
        + (w_time * (1.0 - t_norm))
        + (w_rel * r)
        - (w_transfers * transfer_penalty)
    )

    return round(score, 4)

"""Pareto multi-criteria optimization and NULL-safe fare filter.

Evaluates candidates on:
1. Total journey duration (lower is better)
2. Fare / known cost (lower is better, NULL-safe)
3. Transfers count (lower is better)
4. Overall reliability score (higher is better)
"""

from collections.abc import Sequence

from app.schemas.itinerary import Itinerary


def dominates(a: Itinerary, b: Itinerary) -> bool:
    """
    Check if itinerary A strictly Pareto-dominates itinerary B.
    A dominates B iff A is no worse than B in all criteria, and strictly better in at least one.
    Handles NULL fares honestly: an unverified fare cannot dominate a verified cheaper fare.
    """
    # 1. Duration (lower is better)
    if a.total_duration_minutes > b.total_duration_minutes:
        return False

    # 2. Transfers count (lower is better)
    if a.transfers_count > b.transfers_count:
        return False

    # 3. Reliability (higher is better)
    if a.overall_reliability_score < b.overall_reliability_score:
        return False

    # 4. Cost / Fare (NULL-safe comparison)
    if a.total_fare_inr is not None and b.total_fare_inr is not None:
        if a.total_fare_inr > b.total_fare_inr:
            return False
    elif a.total_fare_inr is None and b.total_fare_inr is not None:
        # A has unknown fare, B has verified fare -> A cannot claim to be as good as B on cost
        return False

    # Now verify that A is strictly better in at least one criterion
    strictly_better = (
        a.total_duration_minutes < b.total_duration_minutes
        or a.transfers_count < b.transfers_count
        or a.overall_reliability_score > b.overall_reliability_score
        or (
            a.total_fare_inr is not None
            and b.total_fare_inr is not None
            and a.total_fare_inr < b.total_fare_inr
        )
    )

    return strictly_better


def filter_pareto_frontier(candidates: Sequence[Itinerary]) -> list[Itinerary]:
    """
    Extract the non-dominated Pareto frontier from candidate itineraries.
    O(N^2) comparison suitable for typical route sets (N <= 100).
    """
    if not candidates:
        return []

    frontier: list[Itinerary] = []

    for i, cand_a in enumerate(candidates):
        is_dominated = False
        for j, cand_b in enumerate(candidates):
            if i != j and dominates(cand_b, cand_a):
                is_dominated = True
                break
        if not is_dominated:
            frontier.append(cand_a)

    return frontier


def apply_null_safe_budget_filter(
    itineraries: Sequence[Itinerary],
    max_budget: float | None,
) -> list[Itinerary]:
    """
    Apply budget constraint with NULL-safe guarantees:
    - If fare <= max_budget: included, marked budget_verified=True.
    - If fare > max_budget: strictly excluded.
    - If fare is None (unverified): included, marked budget_verified=False ('Budget unverified').
    """
    if max_budget is None:
        return list(itineraries)

    filtered: list[Itinerary] = []

    for it in itineraries:
        if it.total_fare_inr is not None:
            if it.total_fare_inr <= max_budget:
                it.budget_verified = True
                filtered.append(it)
            # If > max_budget, discarded
        else:
            # Unverified fare: do not treat as 0, keep with unverified flag
            it.budget_verified = False
            filtered.append(it)

    return filtered

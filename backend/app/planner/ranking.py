"""Ranking and categorization of itineraries into user-facing tabs.

Categories:
1. Best Balance: Balanced trade-off of cost, duration, reliability, and transfers.
2. Cheapest: Lowest total fare (NULL fares sorted with unverified notice).
3. Fastest: Minimum total travel time from initial departure to final arrival.
4. Most Reliable: Highest composite reliability score R.
"""

from collections.abc import Sequence

from app.planner.pareto import apply_null_safe_budget_filter, filter_pareto_frontier
from app.planner.scoring import compute_balance_score
from app.schemas.intent import TripIntent
from app.schemas.itinerary import Itinerary, ItineraryResponse


class ItineraryRanker:
    """Ranks and labels Pareto-optimal transit itineraries across 4 categories."""

    def rank(
        self,
        itineraries: Sequence[Itinerary],
        intent: TripIntent,
        query: str = "",
        search_time_ms: float = 0.0,
        max_results_per_tab: int = 5,
    ) -> ItineraryResponse:
        """Categorize itineraries into best_balance, cheapest, fastest, and most_reliable."""
        if not itineraries:
            return ItineraryResponse(
                query=query or intent.raw_query,
                intent=intent,
                best_balance=[],
                cheapest=[],
                fastest=[],
                most_reliable=[],
                total_itineraries=0,
                search_time_ms=search_time_ms,
            )

        # 1. Apply budget filter (NULL-safe)
        budget_filtered = apply_null_safe_budget_filter(itineraries, intent.budget)

        # 2. Extract Pareto frontier
        pareto_candidates = filter_pareto_frontier(budget_filtered)
        if not pareto_candidates:
            pareto_candidates = list(budget_filtered)

        # 3. Calculate min/max for balance score normalization
        known_fares = [it.total_fare_inr for it in pareto_candidates if it.total_fare_inr is not None]
        min_cost = min(known_fares) if known_fares else 0.0
        max_cost = max(known_fares) if known_fares else 0.0

        durations = [it.total_duration_minutes for it in pareto_candidates]
        min_time = min(durations) if durations else 0.0
        max_time = max(durations) if durations else 0.0

        # Assign balance score to each itinerary
        for it in pareto_candidates:
            it.balance_score = compute_balance_score(
                itinerary=it,
                min_cost=min_cost,
                max_cost=max_cost,
                min_time=min_time,
                max_time=max_time,
            )

        # 4. Generate Rankings for Each Tab
        # Tab 1: Best Balance (descending score)
        best_balance_list = sorted(
            [it.model_copy(deep=True) for it in pareto_candidates],
            key=lambda x: (x.balance_score, -x.total_duration_minutes),
            reverse=True,
        )
        if best_balance_list:
            if "Best Overall" not in best_balance_list[0].badges:
                best_balance_list[0].badges.append("Best Overall")
            best_balance_list[0].category_tags.append("balance")

        # Tab 2: Cheapest (ascending known fare, unknown fares last)
        cheapest_list = sorted(
            [it.model_copy(deep=True) for it in pareto_candidates],
            key=lambda x: (
                x.total_fare_inr is None,
                x.total_fare_inr if x.total_fare_inr is not None else float("inf"),
                x.total_duration_minutes,
            ),
        )
        if cheapest_list and cheapest_list[0].total_fare_inr is not None:
            if "Cheapest Option" not in cheapest_list[0].badges:
                cheapest_list[0].badges.append("Cheapest Option")
            cheapest_list[0].category_tags.append("cheapest")

        # Tab 3: Fastest (ascending total duration)
        fastest_list = sorted(
            [it.model_copy(deep=True) for it in pareto_candidates],
            key=lambda x: (x.total_duration_minutes, -x.overall_reliability_score),
        )
        if fastest_list:
            if "Fastest Route" not in fastest_list[0].badges:
                fastest_list[0].badges.append("Fastest Route")
            fastest_list[0].category_tags.append("fastest")

        # Tab 4: Most Reliable (descending reliability score)
        reliable_list = sorted(
            [it.model_copy(deep=True) for it in pareto_candidates],
            key=lambda x: (x.overall_reliability_score, x.balance_score),
            reverse=True,
        )
        if reliable_list:
            if "Most Reliable" not in reliable_list[0].badges:
                reliable_list[0].badges.append("Most Reliable")
            reliable_list[0].category_tags.append("reliable")

        return ItineraryResponse(
            query=query or intent.raw_query,
            intent=intent,
            best_balance=best_balance_list[:max_results_per_tab],
            cheapest=cheapest_list[:max_results_per_tab],
            fastest=fastest_list[:max_results_per_tab],
            most_reliable=reliable_list[:max_results_per_tab],
            total_itineraries=len(pareto_candidates),
            search_time_ms=search_time_ms,
        )


default_ranker = ItineraryRanker()

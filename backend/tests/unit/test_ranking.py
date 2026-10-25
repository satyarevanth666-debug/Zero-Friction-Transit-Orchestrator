"""Unit and property-based tests for Pareto optimization and ranking engine."""

from hypothesis import given
from hypothesis import strategies as st

from app.planner.pareto import apply_null_safe_budget_filter, dominates, filter_pareto_frontier
from app.planner.ranking import ItineraryRanker
from app.schemas.intent import TripIntent
from app.schemas.itinerary import Itinerary


def make_dummy_itinerary(
    it_id: str,
    duration: int,
    fare: float | None,
    transfers: int,
    reliability: float,
) -> Itinerary:
    """Helper to instantiate test itineraries."""
    return Itinerary(
        id=it_id,
        legs=[],
        total_duration_minutes=duration,
        departure_time="08:00",
        arrival_time="12:00",
        total_fare_inr=fare,
        transfers_count=transfers,
        overall_reliability_score=reliability,
        is_fare_verified=(fare is not None),
    )


# ==============================================================================
# 1. Pareto Dominance Tests
# ==============================================================================

def test_strictly_better_candidate_dominates() -> None:
    # A is faster, cheaper, fewer transfers, higher reliability
    a = make_dummy_itinerary("A", duration=180, fare=400.0, transfers=0, reliability=0.95)
    b = make_dummy_itinerary("B", duration=240, fare=600.0, transfers=1, reliability=0.80)

    assert dominates(a, b) is True
    assert dominates(b, a) is False


def test_tradeoff_candidates_do_not_dominate() -> None:
    # A is faster but more expensive; B is slower but cheaper
    a = make_dummy_itinerary("A", duration=180, fare=800.0, transfers=0, reliability=0.90)
    b = make_dummy_itinerary("B", duration=240, fare=400.0, transfers=0, reliability=0.90)

    assert dominates(a, b) is False
    assert dominates(b, a) is False


def test_null_safe_fare_dominance() -> None:
    # A has unverified fare (None), B has verified cheap fare 300
    # A cannot dominate B on cost even if faster
    a = make_dummy_itinerary("A", duration=180, fare=None, transfers=0, reliability=0.90)
    b = make_dummy_itinerary("B", duration=200, fare=300.0, transfers=0, reliability=0.90)

    assert dominates(a, b) is False


def test_pareto_frontier_filtering() -> None:
    a = make_dummy_itinerary("A", duration=180, fare=500.0, transfers=0, reliability=0.90)
    b = make_dummy_itinerary("B", duration=240, fare=300.0, transfers=0, reliability=0.90)
    c_dominated = make_dummy_itinerary("C", duration=260, fare=600.0, transfers=1, reliability=0.80)

    frontier = filter_pareto_frontier([a, b, c_dominated])
    frontier_ids = [it.id for it in frontier]

    assert "A" in frontier_ids
    assert "B" in frontier_ids
    assert "C" not in frontier_ids


# ==============================================================================
# 2. Property-Based Testing (Hypothesis): Anti-symmetry and Irreflexivity
# ==============================================================================

@given(
    d1=st.integers(min_value=30, max_value=1440),
    f1=st.floats(min_value=50.0, max_value=5000.0),
    t1=st.integers(min_value=0, max_value=3),
    r1=st.floats(min_value=0.1, max_value=1.0),
    d2=st.integers(min_value=30, max_value=1440),
    f2=st.floats(min_value=50.0, max_value=5000.0),
    t2=st.integers(min_value=0, max_value=3),
    r2=st.floats(min_value=0.1, max_value=1.0),
)
def test_pareto_anti_symmetry_property(
    d1: int, f1: float, t1: int, r1: float,
    d2: int, f2: float, t2: int, r2: float,
) -> None:
    """An itinerary cannot dominate another if the other dominates it (Anti-symmetry)."""
    it1 = make_dummy_itinerary("1", d1, f1, t1, r1)
    it2 = make_dummy_itinerary("2", d2, f2, t2, r2)

    dom_1_2 = dominates(it1, it2)
    dom_2_1 = dominates(it2, it1)

    assert not (dom_1_2 and dom_2_1)


@given(
    d=st.integers(min_value=30, max_value=1440),
    f=st.floats(min_value=50.0, max_value=5000.0),
    t=st.integers(min_value=0, max_value=3),
    r=st.floats(min_value=0.1, max_value=1.0),
)
def test_pareto_irreflexivity_property(d: int, f: float, t: int, r: float) -> None:
    """An itinerary cannot dominate itself (Irreflexivity)."""
    it = make_dummy_itinerary("self", d, f, t, r)
    assert dominates(it, it) is False


# ==============================================================================
# 3. NULL-Safe Budget Filtering Tests
# ==============================================================================

def test_null_safe_budget_filter() -> None:
    it_cheap = make_dummy_itinerary("cheap", duration=200, fare=450.0, transfers=0, reliability=0.9)
    it_expensive = make_dummy_itinerary("exp", duration=200, fare=1200.0, transfers=0, reliability=0.9)
    it_unknown = make_dummy_itinerary("unk", duration=200, fare=None, transfers=0, reliability=0.9)

    # Budget ₹800
    res = apply_null_safe_budget_filter([it_cheap, it_expensive, it_unknown], max_budget=800.0)
    res_ids = [it.id for it in res]

    assert "cheap" in res_ids
    assert it_cheap.budget_verified is True

    # ₹1200 exceeds ₹800 -> strictly excluded
    assert "exp" not in res_ids

    # Unknown fare -> kept honestly with budget_verified=False
    assert "unk" in res_ids
    assert it_unknown.budget_verified is False


# ==============================================================================
# 4. Tab Rankings and Categorization Tests
# ==============================================================================

def test_ranker_tab_categorization() -> None:
    # Option 1: Balanced
    it1 = make_dummy_itinerary("1", duration=240, fare=500.0, transfers=0, reliability=0.90)
    # Option 2: Fastest but higher cost
    it2 = make_dummy_itinerary("2", duration=150, fare=1200.0, transfers=0, reliability=0.85)
    # Option 3: Cheapest but longer duration
    it3 = make_dummy_itinerary("3", duration=360, fare=250.0, transfers=1, reliability=0.80)
    # Option 4: Most reliable (all confirmed)
    it4 = make_dummy_itinerary("4", duration=250, fare=600.0, transfers=0, reliability=1.00)

    ranker = ItineraryRanker()
    intent = TripIntent(raw_query="test query")

    response = ranker.rank(
        itineraries=[it1, it2, it3, it4],
        intent=intent,
        query="Bangalore to Vijayawada",
    )

    assert response.total_itineraries >= 3

    # Fastest tab top item must be Option 2 (150 min)
    assert response.fastest[0].id == "2"
    assert "Fastest Route" in response.fastest[0].badges

    # Cheapest tab top item must be Option 3 (₹250)
    assert response.cheapest[0].id == "3"
    assert "Cheapest Option" in response.cheapest[0].badges

    # Most Reliable tab top item must be Option 4 (1.00)
    assert response.most_reliable[0].id == "4"
    assert "Most Reliable" in response.most_reliable[0].badges

    # Best balance has assigned badges
    assert len(response.best_balance) > 0
    assert response.best_balance[0].balance_score > 0.0

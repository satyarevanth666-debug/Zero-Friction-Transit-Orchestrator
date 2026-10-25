"""Fuzzy and exact place resolution engine using RapidFuzz and Gazetteer."""

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.places.gazetteer import Gazetteer, Place, default_gazetteer


@dataclass
class MatchResult:
    """Outcome of a place search or fuzzy match."""
    place: Place
    score: float
    match_type: str  # "exact_code", "exact_alias", "fuzzy"
    matched_term: str


class PlaceMatcher:
    """Resolves natural language location names, codes, typos, and multilingual aliases."""

    def __init__(
        self,
        gazetteer: Gazetteer | None = None,
        fuzzy_threshold: float = 88.0,
    ) -> None:
        self.gazetteer = gazetteer or default_gazetteer
        self.fuzzy_threshold = fuzzy_threshold

    def match(self, text: str) -> MatchResult | None:
        """
        Resolve a place name or query string into a canonical Place entity.
        Returns None if no candidate satisfies the strict confidence threshold.
        """
        clean_text = text.strip()
        if not clean_text or len(clean_text) < 2:
            return None

        # 1. Exact Station Code Match (e.g. "BZA", "DMM", "SC", "NDLS")
        upper_code = clean_text.upper()
        place_by_code = self.gazetteer.get_by_code(upper_code)
        if place_by_code:
            return MatchResult(
                place=place_by_code,
                score=100.0,
                match_type="exact_code",
                matched_term=upper_code,
            )

        # 2. Exact Name or Alias Match (case-insensitive)
        lower_text = clean_text.lower()
        place_by_alias = self.gazetteer.get_exact_by_alias(lower_text)
        if place_by_alias:
            return MatchResult(
                place=place_by_alias,
                score=100.0,
                match_type="exact_alias",
                matched_term=clean_text,
            )

        # 3. RapidFuzz Fuzzy Match across all known alias keys
        alias_keys = self.gazetteer.all_alias_keys()
        if not alias_keys:
            return None

        # RapidFuzz extractOne using token_sort_ratio for robust word-order tolerance
        best_match = process.extractOne(
            lower_text,
            alias_keys,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=self.fuzzy_threshold,
        )

        if best_match:
            matched_key, score, _ = best_match
            matched_place = self.gazetteer.get_exact_by_alias(matched_key)
            if matched_place:
                return MatchResult(
                    place=matched_place,
                    score=float(score),
                    match_type="fuzzy",
                    matched_term=matched_key,
                )

        # Try WRatio for partial word matching if token_sort didn't reach threshold
        best_wratio = process.extractOne(
            lower_text,
            alias_keys,
            scorer=fuzz.WRatio,
            score_cutoff=self.fuzzy_threshold,
        )
        if best_wratio:
            matched_key, score, _ = best_wratio
            matched_place = self.gazetteer.get_exact_by_alias(matched_key)
            if matched_place:
                return MatchResult(
                    place=matched_place,
                    score=float(score),
                    match_type="fuzzy",
                    matched_term=matched_key,
                )

        # Below threshold -> Strictly return None (Anti-hallucination principle)
        return None

    def suggest(self, query: str, limit: int = 5) -> list[MatchResult]:
        """Provide autocomplete suggestions for search bar."""
        clean = query.strip().lower()
        if not clean:
            return []

        results: list[MatchResult] = []
        seen_ids: set[str] = set()

        # Check prefix matches first
        for key in self.gazetteer.all_alias_keys():
            if key.startswith(clean):
                place = self.gazetteer.get_exact_by_alias(key)
                if place and place.id not in seen_ids:
                    results.append(
                        MatchResult(place=place, score=100.0, match_type="prefix", matched_term=key)
                    )
                    seen_ids.add(place.id)
                    if len(results) >= limit:
                        return results

        # Fuzzy suggestions for typos
        alias_keys = self.gazetteer.all_alias_keys()
        fuzzy_matches = process.extract(
            clean,
            alias_keys,
            scorer=fuzz.WRatio,
            limit=limit * 2,
            score_cutoff=70.0,
        )
        for matched_key, score, _ in fuzzy_matches:
            place = self.gazetteer.get_exact_by_alias(matched_key)
            if place and place.id not in seen_ids:
                results.append(
                    MatchResult(place=place, score=float(score), match_type="fuzzy", matched_term=matched_key)
                )
                seen_ids.add(place.id)
                if len(results) >= limit:
                    break

        return results


# Global place matcher instance
default_matcher = PlaceMatcher()

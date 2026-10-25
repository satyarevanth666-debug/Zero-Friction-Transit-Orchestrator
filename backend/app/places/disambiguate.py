"""Disambiguation handler for duplicate place names and multi-station city clusters."""

from dataclasses import dataclass, field

from app.places.gazetteer import Gazetteer, Place, default_gazetteer
from app.places.matching import PlaceMatcher, default_matcher


@dataclass
class DisambiguationCandidate:
    """A selectable option for resolving ambiguous place queries."""
    id: str
    name: str
    state: str
    station_code: str | None
    place_type: str
    description: str


@dataclass
class DisambiguationResult:
    """Outcome of disambiguation analysis."""
    is_ambiguous: bool
    query_text: str
    prompt: str | None = None
    candidates: list[DisambiguationCandidate] = field(default_factory=list)
    resolved_place: Place | None = None
    member_stations: list[str] = field(default_factory=list)


# Known homonyms and duplicate place names across Indian states
AMBIGUOUS_NAMES_MAP: dict[str, list[str]] = {
    "aurangabad": ["AWB", "AUBR"],
    "bilaspur": ["BSP", "CITY_BILASPUR_HP"],
    "rampur": ["RMFO", "CITY_RAMPUR_BH"],
}


class PlaceDisambiguator:
    """Detects and resolves geographic homonyms and multi-station metropolitan clusters."""

    def __init__(
        self,
        gazetteer: Gazetteer | None = None,
        matcher: PlaceMatcher | None = None,
    ) -> None:
        self.gazetteer = gazetteer or default_gazetteer
        self.matcher = matcher or default_matcher

    def resolve(self, text: str) -> DisambiguationResult:
        """
        Analyze place input. If input unambiguously specifies a place or includes
        state qualifiers, resolves immediately. Otherwise returns disambiguation choices.
        """
        clean = text.strip().lower()
        if not clean:
            return DisambiguationResult(is_ambiguous=False, query_text=text)

        # 1. Check if the raw text is a known ambiguous name without state qualifier
        for ambig_key, place_ids in AMBIGUOUS_NAMES_MAP.items():
            if clean == ambig_key:
                candidates: list[DisambiguationCandidate] = []
                for p_id in place_ids:
                    p = self.gazetteer.get_by_id(p_id)
                    if p:
                        desc = f"{p.name}, {p.state}"
                        if p.station_code:
                            desc += f" ({p.station_code})"
                        candidates.append(
                            DisambiguationCandidate(
                                id=p.id,
                                name=p.name,
                                state=p.state,
                                station_code=p.station_code,
                                place_type=p.place_type,
                                description=desc,
                            )
                        )
                return DisambiguationResult(
                    is_ambiguous=True,
                    query_text=text,
                    prompt=f"Multiple places named '{text}' found. Please select:",
                    candidates=candidates,
                )

        # 2. Use Matcher to find best candidate
        match_res = self.matcher.match(text)
        if not match_res:
            return DisambiguationResult(is_ambiguous=False, query_text=text, resolved_place=None)

        matched_place = match_res.place

        # 3. Handle Multi-Station City Clusters (e.g. Hyderabad, Bengaluru, Chennai)
        if matched_place.place_type == "city" and matched_place.member_station_codes:
            return DisambiguationResult(
                is_ambiguous=False,
                query_text=text,
                resolved_place=matched_place,
                member_stations=matched_place.member_station_codes,
            )

        # 4. Unambiguous direct station/city match
        return DisambiguationResult(
            is_ambiguous=False,
            query_text=text,
            resolved_place=matched_place,
            member_stations=[matched_place.station_code] if matched_place.station_code else [],
        )


default_disambiguator = PlaceDisambiguator()

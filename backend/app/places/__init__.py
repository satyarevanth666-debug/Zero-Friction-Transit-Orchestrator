"""Places package with gazetteer, fuzzy matching, and disambiguation."""

from app.places.disambiguate import (
    DisambiguationCandidate,
    DisambiguationResult,
    PlaceDisambiguator,
    default_disambiguator,
)
from app.places.gazetteer import Gazetteer, Place, default_gazetteer
from app.places.matching import MatchResult, PlaceMatcher, default_matcher

__all__ = [
    "DisambiguationCandidate",
    "DisambiguationResult",
    "Gazetteer",
    "MatchResult",
    "Place",
    "PlaceDisambiguator",
    "PlaceMatcher",
    "default_disambiguator",
    "default_gazetteer",
    "default_matcher",
]

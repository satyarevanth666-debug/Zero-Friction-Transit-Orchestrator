"""Hybrid Parser merging rule-based extraction with LLM fallback.

Applies field-level confidence scoring and disambiguation slot detection.
Adheres strictly to the anti-hallucination directive: LLM suggestions for places
are validated against the local gazetteer before acceptance.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from app.config import settings
from app.parsing.llm_parser import LLMParser, default_llm_parser
from app.parsing.rules import RuleBasedParser, default_rule_parser
from app.places.disambiguate import PlaceDisambiguator, default_disambiguator
from app.places.matching import PlaceMatcher, default_matcher
from app.schemas.intent import (
    TimeRange,
    TripIntent,
)

logger = structlog.get_logger("zero-friction-transit")

# Confidence thresholds
CONFIDENCE_THRESHOLD_HIGH = 0.85
CONFIDENCE_THRESHOLD_ACCEPTABLE = 0.70


class HybridParser:
    """
    Combines high-speed deterministic regex/rules with Ollama LLM fallback.
    Maintains NULL-safe, grounded data truth.
    """

    def __init__(
        self,
        rule_parser: RuleBasedParser | None = None,
        llm_parser: LLMParser | None = None,
        disambiguator: PlaceDisambiguator | None = None,
        matcher: PlaceMatcher | None = None,
    ) -> None:
        self.rule_parser = rule_parser or default_rule_parser
        self.llm_parser = llm_parser or default_llm_parser
        self.disambiguator = disambiguator or default_disambiguator
        self.matcher = matcher or default_matcher
        self.tz = ZoneInfo(settings.TIMEZONE)

    def parse(
        self,
        query: str,
        reference_datetime: datetime | None = None,
    ) -> TripIntent:
        """Parse query using Rule Engine with optional LLM fallback for low-confidence fields."""
        ref_dt = reference_datetime or datetime.now(self.tz)
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=self.tz)

        # 1. Execute fast deterministic Rule-based Parser
        intent = self.rule_parser.parse(query, reference_datetime=ref_dt)
        conf = intent.confidence

        # Determine whether LLM fallback is warranted
        needs_llm = (
            conf.origin < CONFIDENCE_THRESHOLD_ACCEPTABLE
            or conf.destination < CONFIDENCE_THRESHOLD_ACCEPTABLE
            or conf.departure_date < CONFIDENCE_THRESHOLD_ACCEPTABLE
        ) and settings.LLM_ENABLED

        # If rule parser is fully confident or LLM is disabled, return rule intent
        if not needs_llm:
            return intent

        # 2. Invoke LLM for disambiguation / missing slot fallback
        logger.debug("Invoking LLM parser for low-confidence slots", query=query[:50])
        llm_data = self.llm_parser.parse(query, reference_datetime=ref_dt)

        if not llm_data:
            # LLM unavailable or timed out -> return rule output gracefully
            return intent

        # 3. Merge LLM extractions safely
        merged_intent = self._merge_extractions(intent, llm_data, ref_dt)
        merged_intent.parser_used = "hybrid"
        return merged_intent

    def _merge_extractions(
        self,
        rule_intent: TripIntent,
        llm_dict: dict[str, Any],
        ref_dt: datetime,
    ) -> TripIntent:
        """Merge rule intent with LLM data, verifying places against gazetteer."""
        intent = rule_intent.model_copy(deep=True)
        conf = intent.confidence

        # 1. Origin fallback if rule origin confidence is low
        if conf.origin < CONFIDENCE_THRESHOLD_ACCEPTABLE and llm_dict.get("origin"):
            llm_orig = str(llm_dict["origin"]).strip()
            res = self.disambiguator.resolve(llm_orig)
            if res.resolved_place:
                intent.origin = res.resolved_place.name
                intent.origin_station_code = res.resolved_place.station_code
                intent.origin_cluster = res.member_stations
                conf.origin = 0.85
                # Remove origin ambiguity if previously added
                intent.disambiguation_slots = [
                    s for s in intent.disambiguation_slots if s.field != "origin"
                ]

        # 2. Destination fallback if rule destination confidence is low
        if conf.destination < CONFIDENCE_THRESHOLD_ACCEPTABLE and llm_dict.get("destination"):
            llm_dest = str(llm_dict["destination"]).strip()
            res = self.disambiguator.resolve(llm_dest)
            if res.resolved_place:
                intent.destination = res.resolved_place.name
                intent.destination_station_code = res.resolved_place.station_code
                intent.destination_cluster = res.member_stations
                conf.destination = 0.85
                intent.disambiguation_slots = [
                    s for s in intent.disambiguation_slots if s.field != "destination"
                ]

        # 3. Departure Date fallback
        if conf.departure_date < CONFIDENCE_THRESHOLD_ACCEPTABLE and llm_dict.get("departure_date"):
            cand_date = str(llm_dict["departure_date"]).strip()
            # Verify ISO format YYYY-MM-DD
            try:
                datetime.strptime(cand_date, "%Y-%m-%d")
                intent.departure_date = cand_date
                conf.departure_date = 0.85
            except ValueError:
                pass

        # 4. Budget fallback
        if intent.budget is None and llm_dict.get("budget") is not None:
            try:
                val = float(llm_dict["budget"])
                intent.budget = val
                conf.budget = 0.85
            except (ValueError, TypeError):
                pass

        # 5. Time range fallback
        if intent.time_range is None and isinstance(llm_dict.get("time_range"), dict):
            tr_dict = llm_dict["time_range"]
            if "start_time" in tr_dict and "end_time" in tr_dict:
                intent.time_range = TimeRange(
                    start_time=str(tr_dict["start_time"]),
                    end_time=str(tr_dict["end_time"]),
                    label=tr_dict.get("label"),
                )
                conf.time_range = 0.85

        # 6. Modes
        if not intent.mode_preference and isinstance(llm_dict.get("mode_preference"), list):
            intent.mode_preference = [str(m).lower() for m in llm_dict["mode_preference"]]
            conf.mode_preference = 0.85

        if not intent.excluded_modes and isinstance(llm_dict.get("excluded_modes"), list):
            intent.excluded_modes = [str(m).lower() for m in llm_dict["excluded_modes"]]

        # 7. Classes
        if not intent.class_preference and isinstance(llm_dict.get("class_preference"), list):
            intent.class_preference = [str(c).upper() for c in llm_dict["class_preference"]]
            conf.class_preference = 0.85

        # 8. Passengers
        if intent.passengers == 1 and llm_dict.get("passengers"):
            try:
                p_cnt = int(llm_dict["passengers"])
                if p_cnt > 1:
                    intent.passengers = p_cnt
                    conf.passengers = 0.85
            except (ValueError, TypeError):
                pass

        # Recalculate overall
        fields_to_eval = [
            conf.origin,
            conf.destination,
            conf.departure_date,
        ]
        conf.overall = round(sum(fields_to_eval) / max(len(fields_to_eval), 1), 2)
        intent.confidence = conf

        return intent


default_hybrid_parser = HybridParser()

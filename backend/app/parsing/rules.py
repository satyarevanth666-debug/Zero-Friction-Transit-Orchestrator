"""Deterministic rule-based natural language parser for Indian travel queries.

Extracts origin, destination, dates, times, budget, modes, classes, passengers,
and constraints using regular expressions, dateparser, and the local gazetteer.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import dateparser

from app.config import settings
from app.places.disambiguate import PlaceDisambiguator, default_disambiguator
from app.schemas.intent import (
    AmbiguityCandidate,
    AmbiguitySlot,
    FieldConfidence,
    SortOption,
    TimeRange,
    TripIntent,
)

# Standard time windows
TIME_WINDOWS: dict[str, tuple[str, str]] = {
    "early morning": ("04:00", "07:59"),
    "morning": ("06:00", "11:59"),
    "afternoon": ("12:00", "15:59"),
    "evening": ("16:00", "21:00"),
    "night": ("21:00", "23:59"),
}

# Stopwords to strip from place tokens
PLACE_NOISE_WORDS = {
    "find", "me", "a", "an", "the", "route", "trip", "ticket", "tickets",
    "cheap", "cheapest", "fast", "fastest", "best", "reliable", "combined",
    "train", "trains", "bus", "buses", "flight", "flights", "please", "can",
    "you", "show", "book", "get", "need", "want", "for", "on", "in", "at",
    "travel", "journey", "going", "leave", "leaving", "direct", "non-stop",
}


class RuleBasedParser:
    """Deterministic extractor for travel queries."""

    def __init__(self, disambiguator: PlaceDisambiguator | None = None) -> None:
        self.disambiguator = disambiguator or default_disambiguator
        self.tz = ZoneInfo(settings.TIMEZONE)

    def parse(
        self,
        query: str,
        reference_datetime: datetime | None = None,
    ) -> TripIntent:
        """Parse natural language query into a structured TripIntent."""
        ref_dt = reference_datetime or datetime.now(self.tz)
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=self.tz)

        intent = TripIntent(raw_query=query, parser_used="rules")
        confidence = FieldConfidence()

        # 1. Budget extraction
        budget, b_conf = self._extract_budget(query)
        if budget is not None:
            intent.budget = budget
            confidence.budget = b_conf

        # 2. Passengers extraction
        passengers, p_conf = self._extract_passengers(query)
        intent.passengers = passengers
        confidence.passengers = p_conf

        # 3. Class preferences extraction
        classes, cl_conf = self._extract_classes(query)
        intent.class_preference = classes
        confidence.class_preference = cl_conf

        # 4. Mode preferences and exclusions
        pref_modes, excl_modes, m_conf = self._extract_modes(query)
        intent.mode_preference = pref_modes
        intent.excluded_modes = excl_modes
        confidence.mode_preference = m_conf

        # 5. Direct only
        direct_only, d_conf = self._extract_direct_only(query)
        intent.direct_only = direct_only
        confidence.direct_only = d_conf

        # 6. Sort option
        sort_by, s_conf = self._extract_sort_by(query)
        intent.sort_by = sort_by
        confidence.sort_by = s_conf

        # 7. Time range (morning, evening, after 5pm, etc.)
        time_range, t_conf = self._extract_time_range(query)
        intent.time_range = time_range
        confidence.time_range = t_conf

        # 8. Return trip check and dates
        is_return, return_date, dep_date, date_conf = self._extract_dates(query, ref_dt)
        intent.is_return = is_return
        intent.return_date = return_date
        intent.departure_date = dep_date
        confidence.departure_date = date_conf

        # 9. Origin and Destination extraction & disambiguation
        self._extract_locations(query, intent, confidence)

        # Calculate overall confidence
        fields_to_eval = [
            confidence.origin,
            confidence.destination,
            confidence.departure_date,
        ]
        confidence.overall = round(sum(fields_to_eval) / max(len(fields_to_eval), 1), 2)
        intent.confidence = confidence

        return intent

    def _extract_budget(self, text: str) -> tuple[float | None, float]:
        """Extract monetary budget in INR (₹, Rs, rupees)."""
        # Currency symbol or Rs prefix e.g. ₹800, ₹ 1,200, Rs. 800, Rs 1500
        p1 = re.search(
            r"(?:₹|rs\.?|inr)\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if p1:
            val_str = p1.group(1).replace(",", "")
            try:
                return float(val_str), 1.0
            except ValueError:
                pass

        # Amount followed by currency e.g. 800 rs, 1200 rupees
        p2 = re.search(
            r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]{1,2})?)\s*(?:₹|rs\.?|inr|rupees?)",
            text,
            re.IGNORECASE,
        )
        if p2:
            val_str = p2.group(1).replace(",", "")
            try:
                return float(val_str), 1.0
            except ValueError:
                pass

        # Keywords: under 800, below 1200, max 2000, budget 800
        p3 = re.search(
            r"\b(?:under|below|less\s+than|max(?:imum)?|budget(?:\s+of)?|within)\s*(?:₹|rs\.?|inr|rupees?)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if p3:
            val_str = p3.group(1).replace(",", "")
            # Avoid capturing times like 'under 2 hours'
            if not re.search(r"\b(?:hours?|hrs?|minutes?|mins?|days?)\b", text[p3.end():p3.end() + 10], re.IGNORECASE):
                try:
                    return float(val_str), 0.95
                except ValueError:
                    pass

        return None, 0.0

    def _extract_passengers(self, text: str) -> tuple[int, float]:
        """Extract passenger count (defaults to 1)."""
        # "2 people", "3 passengers", "2 adults", "4 tickets", "2 persons"
        m1 = re.search(
            r"\b([1-9]|10)\s*(?:passengers?|people|persons?|adults?|tickets?|pax)\b",
            text,
            re.IGNORECASE,
        )
        if m1:
            return int(m1.group(1)), 1.0

        # "for 3 passengers" or "for 3 people" or "for 2"
        m2 = re.search(
            r"\bfor\s+([1-9]|10)\b(?!\s*(?:am|pm|hrs?|hours?|rs|inr|rupees?|₹|days?))",
            text,
            re.IGNORECASE,
        )
        if m2:
            return int(m2.group(1)), 0.9

        # "family of 4", "group of 5"
        m3 = re.search(r"\b(?:family|group)\s+of\s+([1-9]|10)\b", text, re.IGNORECASE)
        if m3:
            return int(m3.group(1)), 1.0

        # "me and my friend/wife/husband/brother" -> 2
        if re.search(r"\b(?:me\s+and\s+my|my)\s+(?:friend|wife|husband|colleague|brother|sister|partner|mom|dad)\b", text, re.IGNORECASE):
            return 2, 0.9

        # "3 of us"
        m4 = re.search(r"\b([2-9])\s*of\s*us\b", text, re.IGNORECASE)
        if m4:
            return int(m4.group(1)), 1.0

        # "solo", "solo traveler"
        if re.search(r"\bsolo(?:\s+traveler)?\b", text, re.IGNORECASE):
            return 1, 1.0

        return 1, 0.5  # default 1 passenger with moderate confidence

    def _extract_classes(self, text: str) -> tuple[list[str], float]:
        """Extract rail/bus travel class preferences."""
        classes: list[str] = []

        if re.search(r"\b(?:1ac|1a|first\s+ac|first\s+class)\b", text, re.IGNORECASE):
            classes.append("1A")
        if re.search(r"\b(?:2ac|2a|second\s+ac|2\s*tier\s*ac)\b", text, re.IGNORECASE):
            classes.append("2A")
        if re.search(r"\b(?:3ac|3a|third\s+ac|3\s*tier\s*ac)\b", text, re.IGNORECASE):
            classes.append("3A")
        if re.search(r"\b(?:sleeper|sl|non-?ac)\b", text, re.IGNORECASE):
            classes.append("SL")
        if re.search(r"\b(?:chair\s*car|cc|executive\s*chair\s*car|ec)\b", text, re.IGNORECASE):
            classes.append("CC")
        if re.search(r"\b(?:second\s*sitting|2s)\b", text, re.IGNORECASE):
            classes.append("2S")
        if re.search(r"\bac\s+only\b", text, re.IGNORECASE) or (re.search(r"\bac\b", text, re.IGNORECASE) and not classes and "non-ac" not in text.lower()):
            classes.append("AC")

        conf = 1.0 if classes else 0.0
        return classes, conf

    def _extract_modes(self, text: str) -> tuple[list[str], list[str], float]:
        """Extract preferred and excluded transportation modes."""
        preferred: list[str] = []
        excluded: list[str] = []

        # Exclusions first
        if re.search(r"\b(?:no|avoid|without|exclude)\s+buses?\b", text, re.IGNORECASE):
            excluded.append("bus")
        if re.search(r"\b(?:no|avoid|without|exclude)\s+trains?\b", text, re.IGNORECASE):
            excluded.append("train")
        if re.search(r"\b(?:no|avoid|without|exclude)\s+flights?\b", text, re.IGNORECASE):
            excluded.append("flight")

        # Preferences
        if re.search(r"\b(?:combined\s+)?train\s+and\s+bus\b|\bbus\s+and\s+train\b|\btrain\s+or\s+bus\b", text, re.IGNORECASE):
            preferred.extend(["train", "bus"])
        elif re.search(r"\b(?:trains?\s+only|only\s+trains?|by\s+train)\b", text, re.IGNORECASE):
            preferred.append("train")
        elif re.search(r"\b(?:buses?\s+only|only\s+buses?|by\s+bus)\b", text, re.IGNORECASE):
            preferred.append("bus")
        elif re.search(r"\b(?:flights?\s+only|only\s+flights?|by\s+air|by\s+flight|fly)\b", text, re.IGNORECASE):
            preferred.append("flight")

        conf = 1.0 if (preferred or excluded) else 0.0
        return preferred, excluded, conf

    def _extract_direct_only(self, text: str) -> tuple[bool, float]:
        """Detect non-stop / direct travel constraints."""
        if re.search(r"\b(?:direct\s+only|direct\s+route|non-?stop|without\s+transfers?|no\s+layovers?|no\s+transfers?)\b", text, re.IGNORECASE):
            return True, 1.0
        return False, 0.0

    def _extract_sort_by(self, text: str) -> tuple[SortOption, float]:
        """Detect sorting criteria: balance, cheapest, fastest, reliable."""
        if re.search(r"\b(?:cheapest|lowest\s+fare|low\s+cost|budget\s+friendly|cheap)\b", text, re.IGNORECASE):
            return "cheapest", 1.0
        if re.search(r"\b(?:fastest|quickest|least\s+time|shortest\s+time|quick)\b", text, re.IGNORECASE):
            return "fastest", 1.0
        if re.search(r"\b(?:most\s+reliable|reliable|least\s+delay|punctual|on-?time)\b", text, re.IGNORECASE):
            return "reliable", 1.0
        return "balance", 0.5

    def _extract_time_range(self, text: str) -> tuple[TimeRange | None, float]:
        """Extract explicit times or periods of day (morning, evening, after 5pm)."""
        lower = text.lower()

        # Named time windows
        for label, (start_t, end_t) in TIME_WINDOWS.items():
            if re.search(rf"\b{label}\b", lower):
                return TimeRange(start_time=start_t, end_time=end_t, label=label), 1.0

        # "after 6pm", "after 18:00"
        m_after = re.search(r"\bafter\s+([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?)\b", lower)
        if m_after:
            t = self._normalize_time_str(m_after.group(1))
            if t:
                return TimeRange(start_time=t, end_time="23:59", label="after"), 0.9

        # "before 10am", "before 10:00"
        m_before = re.search(r"\bbefore\s+([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?)\b", lower)
        if m_before:
            t = self._normalize_time_str(m_before.group(1))
            if t:
                return TimeRange(start_time="00:00", end_time=t, label="before"), 0.9

        # "at 5pm", "around 3pm"
        m_at = re.search(r"\b(?:at|around)\s+([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm))\b", lower)
        if m_at:
            t = self._normalize_time_str(m_at.group(1))
            if t:
                # Provide a 2-hour window around specified time
                h, m = map(int, t.split(":"))
                start_h = max(0, h - 1)
                end_h = min(23, h + 2)
                return TimeRange(start_time=f"{start_h:02d}:{m:02d}", end_time=f"{end_h:02d}:{m:02d}", label="around"), 0.85

        return None, 0.0

    def _normalize_time_str(self, raw: str) -> str | None:
        """Convert '6pm', '6:30 am', '18:00' to 'HH:MM'."""
        raw = raw.strip()
        m_ampm = re.match(r"^([0-9]{1,2})(?::([0-9]{2}))?\s*(am|pm)$", raw, re.IGNORECASE)
        if m_ampm:
            hr = int(m_ampm.group(1))
            minute = int(m_ampm.group(2) or 0)
            ampm = m_ampm.group(3).lower()
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
            return f"{hr:02d}:{minute:02d}"

        m_24h = re.match(r"^([0-9]{1,2}):([0-9]{2})$", raw)
        if m_24h:
            hr = int(m_24h.group(1))
            minute = int(m_24h.group(2))
            if 0 <= hr <= 23 and 0 <= minute <= 59:
                return f"{hr:02d}:{minute:02d}"

        return None

    def _extract_dates(
        self,
        text: str,
        ref_dt: datetime,
    ) -> tuple[bool, str | None, str | None, float]:
        """Extract departure date, return date, and round trip flag."""
        is_return = False
        return_date_str: str | None = None
        dep_date_str: str | None = None
        conf = 0.0

        lower = text.lower()

        # Check return trip pattern: "returning Sunday", "and return on Oct 31", "round trip"
        if "round trip" in lower or "round-trip" in lower:
            is_return = True

        return_match = re.search(
            r"\b(?:return(?:ing)?|coming back|back)\s+(?:on\s+)?([a-zA-Z0-9\s]+?)(?:$|\s+(?:under|for|by|with|budget))",
            lower,
        )
        if return_match:
            is_return = True
            cand_ret = return_match.group(1).strip()
            parsed_ret = self._parse_single_date(cand_ret, ref_dt)
            if parsed_ret:
                return_date_str = parsed_ret.strftime("%Y-%m-%d")

        # Now search for departure date expressions
        # Strip out the return segment to prevent collision
        search_text = lower
        if return_match:
            search_text = lower[:return_match.start()] + lower[return_match.end():]

        # Fast keyword matches relative to ref_dt
        if re.search(r"\b(?:today|tonight|this\s+evening)\b", search_text):
            dep_date_str = ref_dt.strftime("%Y-%m-%d")
            conf = 1.0
        elif re.search(r"\bday\s+after\s+tomorrow\b", search_text):
            dep_date_str = (ref_dt + timedelta(days=2)).strftime("%Y-%m-%d")
            conf = 1.0
        elif re.search(r"\btomorrow\b", search_text):
            dep_date_str = (ref_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            conf = 1.0
        elif re.search(r"\b(?:this|coming)\s+weekend\b", search_text):
            # Saturday of this week
            days_until_sat = (5 - ref_dt.weekday()) % 7
            if days_until_sat == 0 and ref_dt.weekday() != 5:
                days_until_sat = 7
            dep_date_str = (ref_dt + timedelta(days=days_until_sat)).strftime("%Y-%m-%d")
            conf = 0.95
        WEEKDAYS = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }

        # Weekday match
        m_day = re.search(
            r"\b(this\s+|next\s+|coming\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            search_text,
            re.IGNORECASE,
        )
        if m_day:
            day_name = m_day.group(2).lower()
            target_wd = WEEKDAYS[day_name]
            curr_wd = ref_dt.weekday()
            days_ahead = (target_wd - curr_wd) % 7
            if days_ahead == 0:
                days_ahead = 7
            dep_date_str = (ref_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            conf = 1.0
        else:
            # Look for explicit patterns like:
            # "30th Oct", "October 30", "2026-10-30"
            date_patterns = [
                r"\b([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+[0-9]{4})?)\b",
                r"\b((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+[0-9]{1,2}(?:st|nd|rd|th)?(?:\s+[0-9]{4})?)\b",
                r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
                r"\b([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})\b",
            ]

            for pat in date_patterns:
                m = re.search(pat, search_text, re.IGNORECASE)
                if m:
                    cand_str = m.group(1).strip()
                    parsed = self._parse_single_date(cand_str, ref_dt)
                    if parsed:
                        dep_date_str = parsed.strftime("%Y-%m-%d")
                        conf = 1.0
                        break

        # If return date was found and departure was not, ensure departure defaults sensibly
        if is_return and not dep_date_str:
            dep_date_str = ref_dt.strftime("%Y-%m-%d")
            conf = 0.8

        return is_return, return_date_str, dep_date_str, conf

    def _parse_single_date(self, text: str, ref_dt: datetime) -> datetime | None:
        """Parse natural language date string using dateparser with naive relative base."""
        # Check weekdays for return dates as well
        WEEKDAYS = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        m_day = re.search(
            r"\b(this\s+|next\s+|coming\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            text,
            re.IGNORECASE,
        )
        if m_day:
            day_name = m_day.group(2).lower()
            target_wd = WEEKDAYS[day_name]
            curr_wd = ref_dt.weekday()
            days_ahead = (target_wd - curr_wd) % 7
            if days_ahead == 0:
                days_ahead = 7
            return ref_dt + timedelta(days=days_ahead)

        try:
            naive_ref = ref_dt.replace(tzinfo=None)
            parsed = dateparser.parse(
                text,
                settings={
                    "RELATIVE_BASE": naive_ref,
                    "PREFER_DATES_FROM": "future",
                },
            )
            return parsed
        except (ValueError, OverflowError):
            return None

    def _clean_place_token(self, token: str) -> str:
        """Strip punctuation and non-place noise words from candidate location text."""
        # Remove punctuation
        token = re.sub(r"[,\.;:\?!\"'()]+", " ", token)
        words = token.strip().split()
        cleaned_words = [w for w in words if w.lower() not in PLACE_NOISE_WORDS]
        return " ".join(cleaned_words).strip()

    def _extract_locations(
        self,
        query: str,
        intent: TripIntent,
        confidence: FieldConfidence,
    ) -> None:
        """Identify origin and destination candidates, resolve against gazetteer."""
        raw_origin: str | None = None
        raw_dest: str | None = None

        # Pattern 1: "from X to Y"
        p_from_to = re.search(
            r"\bfrom\s+(?P<orig>[a-zA-Z0-9\s\.\-]+?)\s+to\s+(?P<dest>[a-zA-Z0-9\s\.\-]+?)(?:\s+(?:on|for|under|by|at|in|tomorrow|today|this|next|with|returning)|$)",
            query,
            re.IGNORECASE,
        )
        if p_from_to:
            raw_origin = p_from_to.group("orig")
            raw_dest = p_from_to.group("dest")

        # Pattern 2: "between X and Y"
        if not raw_origin and not raw_dest:
            p_between = re.search(
                r"\bbetween\s+(?P<orig>[a-zA-Z0-9\s\.\-]+?)\s+and\s+(?P<dest>[a-zA-Z0-9\s\.\-]+?)(?:\s+(?:on|for|under|by|at|in|tomorrow|today|this|next|with|returning)|$)",
                query,
                re.IGNORECASE,
            )
            if p_between:
                raw_origin = p_between.group("orig")
                raw_dest = p_between.group("dest")

        # Pattern 3: "to Y from X"
        if not raw_origin and not raw_dest:
            p_to_from = re.search(
                r"\bto\s+(?P<dest>[a-zA-Z0-9\s\.\-]+?)\s+from\s+(?P<orig>[a-zA-Z0-9\s\.\-]+?)(?:\s+(?:on|for|under|by|at|in|tomorrow|today|this|next|with|returning)|$)",
                query,
                re.IGNORECASE,
            )
            if p_to_from:
                raw_origin = p_to_from.group("orig")
                raw_dest = p_to_from.group("dest")

        # Pattern 4: "X to Y"
        if not raw_origin and not raw_dest:
            p_simple = re.search(
                r"(?:^|\s)(?P<orig>[a-zA-Z0-9\s\.\-]+?)\s+to\s+(?P<dest>[a-zA-Z0-9\s\.\-]+?)(?:\s+(?:on|for|under|by|at|in|tomorrow|today|this|next|with|returning)|$)",
                query,
                re.IGNORECASE,
            )
            if p_simple:
                cand_o = p_simple.group("orig").strip()
                cand_d = p_simple.group("dest").strip()
                # Verify that orig does not start with a non-place sentence opener like "find me a route"
                raw_origin = cand_o
                raw_dest = cand_d

        # Pattern 5: Special case for "route home", "going home", "trip home"
        if re.search(r"\b(?:route|trip|travel|going|get)\s+home\b", query, re.IGNORECASE):
            raw_dest = "home"

        # Clean place tokens
        if raw_origin:
            raw_origin = self._clean_place_token(raw_origin)
        if raw_dest:
            raw_dest = self._clean_place_token(raw_dest)

        # Resolve Origin
        if raw_origin:
            self._resolve_place_slot(
                slot_name="origin",
                token=raw_origin,
                intent=intent,
                confidence=confidence,
            )
        else:
            confidence.origin = 0.0

        # Resolve Destination
        if raw_dest:
            self._resolve_place_slot(
                slot_name="destination",
                token=raw_dest,
                intent=intent,
                confidence=confidence,
            )
        else:
            confidence.destination = 0.0

    def _resolve_place_slot(
        self,
        slot_name: str,
        token: str,
        intent: TripIntent,
        confidence: FieldConfidence,
    ) -> None:
        """Resolve place token with disambiguation, cluster expansion, or ambiguity recording."""
        if not token:
            setattr(confidence, slot_name, 0.0)
            return

        if token.lower() == "home":
            # "home" is a relative destination requiring disambiguation or user profile lookup
            setattr(intent, slot_name, "Home")
            setattr(confidence, slot_name, 0.0)
            intent.disambiguation_slots.append(
                AmbiguitySlot(
                    field=slot_name,
                    raw_token="home",
                    candidates=[],
                    prompt="Please specify your destination station or city (e.g., Vijayawada, Guntur).",
                )
            )
            return

        # Attempt resolution via PlaceDisambiguator
        res = self.disambiguator.resolve(token)

        if res.is_ambiguous:
            # Homonym detected (e.g. Aurangabad MH vs Aurangabad BH)
            setattr(intent, slot_name, token)
            setattr(confidence, slot_name, 0.5)
            candidates = [
                AmbiguityCandidate(
                    id=c.id,
                    name=c.name,
                    state=c.state,
                    station_code=c.station_code,
                    description=c.description,
                )
                for c in res.candidates
            ]
            intent.disambiguation_slots.append(
                AmbiguitySlot(
                    field=slot_name,
                    raw_token=token,
                    candidates=candidates,
                    prompt=res.prompt or f"Multiple places named '{token}' found. Please select:",
                )
            )
            return

        if res.resolved_place:
            p = res.resolved_place
            setattr(intent, slot_name, p.name)
            if slot_name == "origin":
                intent.origin_station_code = p.station_code or (res.member_stations[0] if res.member_stations else None)
                intent.origin_cluster = res.member_stations
                confidence.origin = 1.0
            else:
                intent.destination_station_code = p.station_code or (res.member_stations[0] if res.member_stations else None)
                intent.destination_cluster = res.member_stations
                confidence.destination = 1.0
            return

        # Not resolved against gazetteer -> ungrounded token
        setattr(intent, slot_name, token)
        setattr(confidence, slot_name, 0.0)
        intent.disambiguation_slots.append(
            AmbiguitySlot(
                field=slot_name,
                raw_token=token,
                candidates=[],
                prompt=f"Could not recognize location '{token}'. Please enter a valid city or station name.",
            )
        )


default_rule_parser = RuleBasedParser()

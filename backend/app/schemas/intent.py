"""Trip intent schemas representing structured requirements extracted from natural language."""

from typing import Literal

from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    """Normalized time window constraint (e.g. morning, evening, or explicit interval)."""
    start_time: str = Field(..., description="Start of window in HH:MM (24-hour)")
    end_time: str = Field(..., description="End of window in HH:MM (24-hour)")
    label: str | None = Field(default=None, description="Human label: morning, afternoon, evening, night, custom")


class AmbiguityCandidate(BaseModel):
    """Candidate option when resolving homonyms or ambiguous locations."""
    id: str
    name: str
    state: str
    station_code: str | None = None
    description: str


class AmbiguitySlot(BaseModel):
    """Slot requiring clarification from the user."""
    field: str = Field(..., description="Field name (e.g., origin, destination, date)")
    raw_token: str = Field(..., description="The ambiguous or ungrounded token from user query")
    candidates: list[AmbiguityCandidate] = Field(default_factory=list, description="Candidate matches")
    prompt: str = Field(..., description="Clarification message or question for the user")


class FieldConfidence(BaseModel):
    """Confidence scores (0.0 to 1.0) for individual extracted slots."""
    origin: float = 0.0
    destination: float = 0.0
    departure_date: float = 0.0
    time_range: float = 0.0
    budget: float = 0.0
    passengers: float = 0.0
    mode_preference: float = 0.0
    class_preference: float = 0.0
    direct_only: float = 0.0
    sort_by: float = 0.0
    overall: float = 0.0


SortOption = Literal["balance", "cheapest", "fastest", "reliable"]


class TripIntent(BaseModel):
    """
    Structured trip search intent extracted by the hybrid parser.
    Feeds directly into the deterministic RAPTOR planner.
    """
    origin: str | None = None
    destination: str | None = None
    origin_station_code: str | None = None
    destination_station_code: str | None = None
    origin_cluster: list[str] = Field(default_factory=list, description="Member station codes for origin city cluster")
    destination_cluster: list[str] = Field(default_factory=list, description="Member station codes for destination city cluster")
    departure_date: str | None = None  # Format: YYYY-MM-DD
    time_range: TimeRange | None = None
    budget: float | None = None
    passengers: int = 1
    mode_preference: list[str] = Field(default_factory=list, description="Preferred modes e.g. ['train', 'bus']")
    excluded_modes: list[str] = Field(default_factory=list, description="Excluded modes e.g. ['bus']")
    class_preference: list[str] = Field(default_factory=list, description="Preferred classes e.g. ['AC', 'SL', '3A']")
    direct_only: bool = False
    sort_by: SortOption = "balance"
    is_return: bool = False
    return_date: str | None = None  # Format: YYYY-MM-DD
    confidence: FieldConfidence = Field(default_factory=FieldConfidence)
    disambiguation_slots: list[AmbiguitySlot] = Field(default_factory=list)
    raw_query: str = ""
    parser_used: Literal["rules", "llm", "hybrid"] = "rules"

"""Pydantic schemas for multi-modal travel itineraries, legs, and pricing."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.intent import TripIntent

TruthLevel = Literal[
    "OFFICIAL_TIMETABLE",
    "COMMUNITY_GTFS",
    "LIVE_API",
    "ESTIMATED",
    "USER_PROVIDED",
    "UNKNOWN",
]


class Leg(BaseModel):
    """Single segment/hop in a multi-leg journey."""
    mode: str = Field(..., description="rail | bus | flight | transfer")
    operator: str = Field(..., description="Indian Railways, APSRTC, IndiGo, etc.")
    service_number: str = Field(..., description="12785, 6201, 6E-205, etc.")
    service_name: str = Field(..., description="Kacheguda Express, Amaravathi, etc.")
    from_station_code: str
    from_station_name: str
    to_station_code: str
    to_station_name: str
    departure_time: str = Field(..., description="HH:MM:SS or ISO string")
    arrival_time: str = Field(..., description="HH:MM:SS or ISO string")
    duration_minutes: int
    fare_inr: float | None = Field(default=None, description="NULL-safe fare. None if unknown.")
    truth_level: TruthLevel = "OFFICIAL_TIMETABLE"
    class_code: str | None = None  # "SL", "3A", "2A", "CC", "EXP"
    availability_status: str | None = None  # "CNF", "RAC", "WL", "UNKNOWN"
    waitlist_position: int | None = None
    confirmation_probability: float | None = None
    reliability_score: float = 0.75


class TransferDetail(BaseModel):
    """Connection or layover between consecutive journey legs."""
    from_station_code: str
    to_station_code: str
    buffer_minutes: int
    transfer_type: Literal["same_station", "cross_station"] = "same_station"
    safety_score: float = 1.0
    cost_inr: float | None = None
    notes: str | None = None


class Itinerary(BaseModel):
    """Complete door-to-door or hub-to-hub multi-modal itinerary."""
    id: str
    legs: list[Leg]
    transfers: list[TransferDetail] = Field(default_factory=list)
    total_duration_minutes: int
    departure_time: str
    arrival_time: str
    total_fare_inr: float | None = Field(default=None, description="NULL-safe. None if any leg fare is unknown.")
    is_fare_verified: bool = True
    transfers_count: int = 0
    overall_reliability_score: float = 0.75
    balance_score: float = 0.0
    badges: list[str] = Field(default_factory=list)
    category_tags: list[str] = Field(default_factory=list)
    budget_verified: bool = True


class ItineraryResponse(BaseModel):
    """Unified payload returned to user via REST or streamed SSE."""
    query: str
    intent: TripIntent
    best_balance: list[Itinerary] = Field(default_factory=list)
    cheapest: list[Itinerary] = Field(default_factory=list)
    fastest: list[Itinerary] = Field(default_factory=list)
    most_reliable: list[Itinerary] = Field(default_factory=list)
    total_itineraries: int = 0
    search_time_ms: float = 0.0

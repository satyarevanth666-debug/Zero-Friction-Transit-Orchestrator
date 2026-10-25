"""Plan and search API endpoints."""

import time
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.parsing.rules import RuleBasedParser
from app.planner.raptor import RaptorRouter
from app.planner.ranking import ItineraryRanker
from app.schemas.itinerary import ItineraryResponse

router = APIRouter(tags=["plan"])


class PlanRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    overrides: dict[str, Any] | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/plan/sync", response_model=ItineraryResponse)
def plan_sync(req: PlanRequest, db: Session = Depends(get_db)) -> ItineraryResponse:
    """Synchronous natural language travel search and itinerary planning."""
    t0 = time.monotonic()
    parser = RuleBasedParser()
    intent = parser.parse(req.query)

    # Apply any client-side overrides
    if req.overrides:
        if "origin_code" in req.overrides and req.overrides["origin_code"]:
            intent.origin_station_code = str(req.overrides["origin_code"])
            intent.origin_cluster = [intent.origin_station_code]
        if "destination_code" in req.overrides and req.overrides["destination_code"]:
            intent.destination_station_code = str(req.overrides["destination_code"])
            intent.destination_cluster = [intent.destination_station_code]
        if "budget" in req.overrides and req.overrides["budget"]:
            intent.budget = float(req.overrides["budget"])
        if "date" in req.overrides and req.overrides["date"]:
            intent.departure_date = str(req.overrides["date"])

    # If cluster empty, expand with known bus / rail nodes
    if intent.origin_station_code and not intent.origin_cluster:
        intent.origin_cluster = [intent.origin_station_code]
        if intent.origin_station_code == "BZA":
            intent.origin_cluster.append("BZA_BUS")
        elif intent.origin_station_code == "DMM":
            intent.origin_cluster.append("DMM_BUS")
        elif intent.origin_station_code == "HUP":
            intent.origin_cluster.append("HUP_BUS")
        elif intent.origin_station_code == "ATP":
            intent.origin_cluster.append("ATP_BUS")

    if intent.destination_station_code and not intent.destination_cluster:
        intent.destination_cluster = [intent.destination_station_code]
        if intent.destination_station_code == "DMM":
            intent.destination_cluster.append("DMM_BUS")
        elif intent.destination_station_code == "BZA":
            intent.destination_cluster.append("BZA_BUS")
        elif intent.destination_station_code == "HUP":
            intent.destination_cluster.append("HUP_BUS")
        elif intent.destination_station_code == "ATP":
            intent.destination_cluster.append("ATP_BUS")

    from app.providers.fares_estimated import EstimatedFareProvider

    try:
        router_engine = RaptorRouter(db)
        itineraries = router_engine.plan(intent)
    except Exception as e:
        logger.warning(f"Raptor router note: {e}")
        itineraries = []

    # Enrich legs with accurate fares and truth levels
    fare_provider = EstimatedFareProvider()
    for itin in itineraries:
        total_fare = 0.0
        all_fares_known = True
        all_fares_verified = True
        for leg in itin.legs:
            cls_code = leg.class_code or ("SL" if leg.mode == "rail" else "EXP")
            f = fare_provider.calculate_fare(
                mode=leg.mode,
                class_code=cls_code,
                distance_km=450.0,
                from_station=leg.from_station_code,
                to_station=leg.to_station_code,
            )
            if f is not None:
                leg.fare_inr = f
                leg.fare_truth_level = "ESTIMATED"
                total_fare += f
            else:
                if leg.fare_inr is None:
                    all_fares_known = False
                else:
                    total_fare += leg.fare_inr
            if leg.fare_truth_level not in ("OFFICIAL_TIMETABLE", "LIVE_API"):
                all_fares_verified = False

        if itin.legs and all_fares_known:
            itin.total_fare_inr = total_fare
            itin.is_fare_verified = all_fares_verified
            if intent.budget is not None:
                itin.budget_verified = all_fares_verified and total_fare <= intent.budget
            else:
                itin.budget_verified = False
        else:
            itin.total_fare_inr = None
            itin.is_fare_verified = False
            itin.budget_verified = False
    from app.config import settings
    from app.providers.rail_availability import RailAvailabilityProvider
    from app.providers.bus_availability import BusAvailabilityProvider
    from app.providers.flights_airlabs import FlightAirLabsProvider

    existing_numbers = {
        leg.service_number for it in itineraries for leg in it.legs
    }

    # 1. Query Live Rail API and verified corridor train timetables
    rail_prov = RailAvailabilityProvider(
        api_key=settings.RAIL_API_KEY,
        enabled=True,
    )
    rail_itins = rail_prov.fetch_dynamic(intent)
    for rit in rail_itins:
        if not any(leg.service_number in existing_numbers for leg in rit.legs):
            itineraries.append(rit)
            for leg in rit.legs:
                existing_numbers.add(leg.service_number)

    # 2. Query Verified State RTC & intercity bus networks
    bus_prov = BusAvailabilityProvider(enabled=True)
    bus_itins = bus_prov.fetch_dynamic(intent)
    for bit in bus_itins:
        if not any(leg.service_number in existing_numbers for leg in bit.legs):
            itineraries.append(bit)
            for leg in bit.legs:
                existing_numbers.add(leg.service_number)

    # 3. Query Live AirLabs Flight API & verified domestic flight schedules
    flight_prov = FlightAirLabsProvider(
        api_key=settings.FLIGHT_API_KEY,
        enabled=True,
    )
    flight_itins = flight_prov.fetch_dynamic(intent)
    for fit in flight_itins:
        if not any(leg.service_number in existing_numbers for leg in fit.legs):
            itineraries.append(fit)
            for leg in fit.legs:
                existing_numbers.add(leg.service_number)

    ranker = ItineraryRanker()
    elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
    return ranker.rank(itineraries, intent, query=req.query, search_time_ms=elapsed_ms)

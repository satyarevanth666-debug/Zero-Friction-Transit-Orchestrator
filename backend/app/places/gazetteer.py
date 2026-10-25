"""Comprehensive Gazetteer for Indian transit nodes, cities, and multi-lingual aliases."""

from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.db.models import Alias, City, Station


@dataclass(frozen=True)
class Place:
    """Canonical place representation across railway stations, bus stands, and airports."""
    id: str  # Unique code e.g. "BZA", "CITY_HYD", "DMM_BUS"
    name: str
    state: str
    district: str | None = None
    place_type: str = "station"  # "station", "bus_stand", "airport", "city"
    station_code: str | None = None
    city_name: str | None = None
    lat: float = 0.0
    lon: float = 0.0
    aliases: list[str] = field(default_factory=list)
    member_station_codes: list[str] = field(default_factory=list)  # For city clusters
    is_ambiguous: bool = False
    coverage_tier: str = "B"  # "A" (Deep corridor), "B" (Timetable), "C" (Place only)


# Baseline offline gazetteer dataset covering pan-India nodes and demo corridor
DEFAULT_PLACES: list[dict[str, Any]] = [

    # --- DEMO CORRIDOR & ANDHRA PRADESH (Tier A) ---
    {
        "id": "BZA",
        "name": "Vijayawada Junction",
        "state": "Andhra Pradesh",
        "district": "NTR",
        "place_type": "station",
        "station_code": "BZA",
        "city_name": "Vijayawada",
        "lat": 16.5186,
        "lon": 80.6200,
        "aliases": ["Vijayawada", "Bezawada", "Bejawada", "విజయవాడ", "विजयवाड़ा", "BZA Jn"],
        "coverage_tier": "A",
    },
    {
        "id": "BZA_BUS",
        "name": "Pandit Nehru Bus Station (PNBS)",
        "state": "Andhra Pradesh",
        "district": "NTR",
        "place_type": "bus_stand",
        "station_code": "BZA_BUS",
        "city_name": "Vijayawada",
        "lat": 16.5085,
        "lon": 80.6174,
        "aliases": ["PNBS", "Vijayawada Bus Stand", "PNBS Bus Stand"],
        "coverage_tier": "A",
    },
    {
        "id": "VGA",
        "name": "Vijayawada International Airport",
        "state": "Andhra Pradesh",
        "district": "Krishna",
        "place_type": "airport",
        "station_code": "VGA",
        "city_name": "Vijayawada",
        "lat": 16.5304,
        "lon": 80.7968,
        "aliases": ["Gannavaram Airport", "Vijayawada Airport"],
        "coverage_tier": "A",
    },
    {
        "id": "DMM",
        "name": "Dharmavaram Junction",
        "state": "Andhra Pradesh",
        "district": "Sri Sathya Sai",
        "place_type": "station",
        "station_code": "DMM",
        "city_name": "Dharmavaram",
        "lat": 14.4172,
        "lon": 77.7180,
        "aliases": ["Dharmavaram", "Dharmavaram Jn", "ధర్మవరం", "धर्मवरम"],
        "coverage_tier": "A",
    },
    {
        "id": "DMM_BUS",
        "name": "Dharmavaram APSRTC Bus Stand",
        "state": "Andhra Pradesh",
        "district": "Sri Sathya Sai",
        "place_type": "bus_stand",
        "station_code": "DMM_BUS",
        "city_name": "Dharmavaram",
        "lat": 14.4110,
        "lon": 77.7240,
        "aliases": ["Dharmavaram Bus Stand", "DMM Bus"],
        "coverage_tier": "A",
    },
    {
        "id": "HUP",
        "name": "Hindupur Railway Station",
        "state": "Andhra Pradesh",
        "district": "Sri Sathya Sai",
        "place_type": "station",
        "station_code": "HUP",
        "city_name": "Hindupur",
        "lat": 13.8299,
        "lon": 77.4950,
        "aliases": ["Hindupur", "Hindupoor", "హిందూపురం", "हिंदूपुर", "Hindupuram"],

        "coverage_tier": "A",
    },
    {
        "id": "HUP_BUS",
        "name": "Hindupur Bus Stand",
        "state": "Andhra Pradesh",
        "district": "Sri Sathya Sai",
        "place_type": "bus_stand",
        "station_code": "HUP_BUS",
        "city_name": "Hindupur",
        "lat": 13.8260,
        "lon": 77.4910,
        "aliases": ["Hindupur Bus Station", "HUP Bus"],
        "coverage_tier": "A",
    },
    {
        "id": "ATP",
        "name": "Anantapur Railway Station",
        "state": "Andhra Pradesh",
        "district": "Anantapur",
        "place_type": "station",
        "station_code": "ATP",
        "city_name": "Anantapur",
        "lat": 14.6853,
        "lon": 77.6009,
        "aliases": ["Anantapur", "Ananthapur", "అనంతపురం", "अनंतपुर"],
        "coverage_tier": "A",
    },
    {
        "id": "ATP_BUS",
        "name": "Anantapur Bus Station",
        "state": "Andhra Pradesh",
        "district": "Anantapur",
        "place_type": "bus_stand",
        "station_code": "ATP_BUS",
        "city_name": "Anantapur",
        "lat": 14.6780,
        "lon": 77.5950,
        "aliases": ["Anantapur Bus Stand", "ATP Bus"],
        "coverage_tier": "A",
    },
    {
        "id": "GNT",
        "name": "Guntur Junction",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "place_type": "station",
        "station_code": "GNT",
        "city_name": "Guntur",
        "lat": 16.2974,
        "lon": 80.4438,
        "aliases": ["Guntur", "Guntoor", "గుంటూరు", "गुंटूर"],

        "coverage_tier": "A",
    },
    {
        "id": "GTL",
        "name": "Guntakal Junction",
        "state": "Andhra Pradesh",
        "district": "Anantapur",
        "place_type": "station",
        "station_code": "GTL",
        "city_name": "Guntakal",
        "lat": 15.1667,
        "lon": 77.3667,
        "aliases": ["Guntakal", "గుంతకల్లు", "गुंतकल"],
        "coverage_tier": "A",
    },
    {
        "id": "CITY_AMARAVATI",
        "name": "Amaravati",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "place_type": "city",
        "city_name": "Amaravati",
        "lat": 16.5131,
        "lon": 80.5165,
        "aliases": ["Amaravathi", "అమరావతి", "अमरावती"],
        "member_station_codes": ["BZA", "GNT", "BZA_BUS"],
        "coverage_tier": "A",
    },
    {
        "id": "TPTY",
        "name": "Tirupati Main",
        "state": "Andhra Pradesh",
        "district": "Tirupati",
        "place_type": "station",
        "station_code": "TPTY",
        "city_name": "Tirupati",
        "lat": 13.6288,
        "lon": 79.4210,
        "aliases": ["Tirupati", "Tirupathi", "తిరుపతి", "तिरुपति", "Tirumala"],
        "coverage_tier": "B",
    },
    {
        "id": "VSKP",
        "name": "Visakhapatnam Junction",
        "state": "Andhra Pradesh",
        "district": "Visakhapatnam",
        "place_type": "station",
        "station_code": "VSKP",
        "city_name": "Visakhapatnam",
        "lat": 17.7215,
        "lon": 83.2872,
        "aliases": ["Vizag", "Visakhapatnam", "Waltair", "విశాఖపట్నం", "विशाखापट्टनम"],
        "coverage_tier": "B",
    },

    # --- TELANGANA / HYDERABAD CLUSTER ---
    {
        "id": "CITY_HYDERABAD",
        "name": "Hyderabad",
        "state": "Telangana",
        "district": "Hyderabad",
        "place_type": "city",
        "city_name": "Hyderabad",
        "lat": 17.3850,
        "lon": 78.4867,
        "aliases": ["Hyderabad", "Hyd", "హైదరాబాద్", "हैदराबाद"],
        "member_station_codes": ["SC", "HYB", "KCG", "HYD_AIR"],
        "coverage_tier": "B",
    },
    {
        "id": "SC",
        "name": "Secunderabad Junction",
        "state": "Telangana",
        "district": "Hyderabad",
        "place_type": "station",
        "station_code": "SC",
        "city_name": "Hyderabad",
        "lat": 17.4339,
        "lon": 78.5017,
        "aliases": ["Secunderabad", "సికింద్రాబాద్", "सिकंदराबाद"],
        "coverage_tier": "B",
    },
    {
        "id": "HYB",
        "name": "Hyderabad Deccan (Nampally)",
        "state": "Telangana",
        "district": "Hyderabad",
        "place_type": "station",
        "station_code": "HYB",
        "city_name": "Hyderabad",
        "lat": 17.3920,
        "lon": 78.4680,
        "aliases": ["Nampally", "Hyderabad Deccan", "HYB Nampally"],
        "coverage_tier": "B",
    },
    {
        "id": "KCG",
        "name": "Kacheguda",
        "state": "Telangana",
        "district": "Hyderabad",
        "place_type": "station",
        "station_code": "KCG",
        "city_name": "Hyderabad",
        "lat": 17.3890,
        "lon": 78.5020,
        "aliases": ["Kacheguda Railway Station", "కాచిగూడ", "काचीगुड़ा"],
        "coverage_tier": "B",
    },
    {
        "id": "HYD_AIR",
        "name": "Rajiv Gandhi International Airport",
        "state": "Telangana",
        "district": "Rangareddy",
        "place_type": "airport",
        "station_code": "HYD_AIR",
        "city_name": "Hyderabad",
        "lat": 17.2403,
        "lon": 78.4294,
        "aliases": ["RGIA", "Shamshabad Airport", "Hyderabad Airport"],
        "coverage_tier": "B",
    },

    # --- KARNATAKA / BENGALURU CLUSTER ---
    {
        "id": "CITY_BLR",
        "name": "Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "place_type": "city",
        "city_name": "Bengaluru",
        "lat": 12.9716,
        "lon": 77.5946,
        "aliases": ["Bangalore", "Bengaluru", "బెంగళూరు", "बेंगलुरु", "बेंगलोर"],
        "member_station_codes": ["SBC", "YPR", "SMVB", "BLR_AIR"],
        "coverage_tier": "B",
    },
    {
        "id": "SBC",
        "name": "KSR Bengaluru City Junction",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "place_type": "station",
        "station_code": "SBC",
        "city_name": "Bengaluru",
        "lat": 12.9784,
        "lon": 77.5694,
        "aliases": ["Bangalore City", "Majestic Station", "KSR Bengaluru"],
        "coverage_tier": "B",
    },
    {
        "id": "YPR",
        "name": "Yesvantpur Junction",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "place_type": "station",
        "station_code": "YPR",
        "city_name": "Bengaluru",
        "lat": 13.0242,
        "lon": 77.5457,
        "aliases": ["Yeswantpur", "Yeshwantpur"],
        "coverage_tier": "B",
    },
    {
        "id": "SMVB",
        "name": "Sir M. Visvesvaraya Terminal",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "place_type": "station",
        "station_code": "SMVB",
        "city_name": "Bengaluru",
        "lat": 12.9922,
        "lon": 77.6534,
        "aliases": ["SMVT", "Baiyappanahalli Terminal"],
        "coverage_tier": "B",
    },

    # --- TAMIL NADU / CHENNAI CLUSTER ---
    {
        "id": "CITY_CHENNAI",
        "name": "Chennai",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "place_type": "city",
        "city_name": "Chennai",
        "lat": 13.0827,
        "lon": 80.2707,
        "aliases": ["Madras", "Chennai", "మద్రాస్", "चेन्नई", "मद्रास"],
        "member_station_codes": ["MAS", "MS"],
        "coverage_tier": "B",
    },
    {
        "id": "MAS",
        "name": "Chennai Central",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "place_type": "station",
        "station_code": "MAS",
        "city_name": "Chennai",
        "lat": 13.0827,
        "lon": 80.2757,
        "aliases": ["Puratchi Thalaivar Dr. MGR Central", "Chennai Central"],
        "coverage_tier": "B",
    },
    {
        "id": "MS",
        "name": "Chennai Egmore",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "place_type": "station",
        "station_code": "MS",
        "city_name": "Chennai",
        "lat": 13.0784,
        "lon": 80.2604,
        "aliases": ["Egmore", "Chennai Egmore Station"],
        "coverage_tier": "B",
    },

    # --- DISAMBIGUATION CASUS: AURANGABAD ---
    {
        "id": "AWB",
        "name": "Aurangabad (Chhatrapati Sambhajinagar)",
        "state": "Maharashtra",
        "district": "Chhatrapati Sambhajinagar",
        "place_type": "station",
        "station_code": "AWB",
        "city_name": "Aurangabad",
        "lat": 19.8667,
        "lon": 75.3167,
        "aliases": ["Aurangabad Maharashtra", "Chhatrapati Sambhajinagar", "औरंगाबाद महाराष्ट्र"],
        "is_ambiguous": True,
        "coverage_tier": "B",
    },
    {
        "id": "AUBR",
        "name": "Anugrah Narayan Road (Aurangabad, Bihar)",
        "state": "Bihar",
        "district": "Aurangabad",
        "place_type": "station",
        "station_code": "AUBR",
        "city_name": "Aurangabad",
        "lat": 24.8167,
        "lon": 84.3667,
        "aliases": ["Aurangabad Bihar", "Anugrah Narayan Road", "औरंगाबाद बिहार"],
        "is_ambiguous": True,
        "coverage_tier": "B",
    },

    # --- DISAMBIGUATION CASUS: BILASPUR ---
    {
        "id": "BSP",
        "name": "Bilaspur Junction",
        "state": "Chhattisgarh",
        "district": "Bilaspur",
        "place_type": "station",
        "station_code": "BSP",
        "city_name": "Bilaspur",
        "lat": 22.0800,
        "lon": 82.1800,
        "aliases": ["Bilaspur CG", "बिलासपुर छत्तीसगढ़"],
        "is_ambiguous": True,
        "coverage_tier": "B",
    },
    {
        "id": "CITY_BILASPUR_HP",
        "name": "Bilaspur, Himachal Pradesh",
        "state": "Himachal Pradesh",
        "district": "Bilaspur",
        "place_type": "city",
        "city_name": "Bilaspur",
        "lat": 31.3300,
        "lon": 76.7500,
        "aliases": ["Bilaspur HP", "बिलासपुर हिमाचल"],
        "is_ambiguous": True,
        "coverage_tier": "C",
    },

    # --- DISAMBIGUATION CASUS: RAMPUR ---
    {
        "id": "RMFO",
        "name": "Rampur Junction",
        "state": "Uttar Pradesh",
        "district": "Rampur",
        "place_type": "station",
        "station_code": "RMFO",
        "city_name": "Rampur",
        "lat": 28.8000,
        "lon": 79.0300,
        "aliases": ["Rampur UP", "रामपुर"],
        "is_ambiguous": True,
        "coverage_tier": "B",
    },
    {
        "id": "CITY_RAMPUR_BH",
        "name": "Rampur, Bihar",
        "state": "Bihar",
        "district": "Kaimur",
        "place_type": "city",
        "city_name": "Rampur",
        "lat": 25.0400,
        "lon": 83.6200,
        "aliases": ["Rampur Bihar"],
        "is_ambiguous": True,
        "coverage_tier": "C",
    },

    # --- MAJOR METROS & PAN-INDIA HUBS ---
    {
        "id": "NDLS",
        "name": "New Delhi Railway Station",
        "state": "Delhi",
        "district": "Central Delhi",
        "place_type": "station",
        "station_code": "NDLS",
        "city_name": "Delhi",
        "lat": 28.6427,
        "lon": 77.2195,
        "aliases": ["Delhi", "New Delhi", "नई दिल्ली", "దిల్లీ"],
        "coverage_tier": "B",
    },
    {
        "id": "CSMT",
        "name": "Chhatrapati Shivaji Maharaj Terminus",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "place_type": "station",
        "station_code": "CSMT",
        "city_name": "Mumbai",
        "lat": 18.9400,
        "lon": 72.8353,
        "aliases": ["Mumbai", "Bombay", "VT", "Victoria Terminus", "मुंबई", "ముంబై"],
        "coverage_tier": "B",
    },
    {
        "id": "HWH",
        "name": "Howrah Junction",
        "state": "West Bengal",
        "district": "Howrah",
        "place_type": "station",
        "station_code": "HWH",
        "city_name": "Kolkata",
        "lat": 22.5839,
        "lon": 88.3426,
        "aliases": ["Kolkata", "Calcutta", "Howrah", "कोलकाता", "కోల్‌కతా"],
        "coverage_tier": "B",
    },
    {
        "id": "PNBE",
        "name": "Patna Junction",
        "state": "Bihar",
        "district": "Patna",
        "place_type": "station",
        "station_code": "PNBE",
        "city_name": "Patna",
        "lat": 25.6022,
        "lon": 85.1376,
        "aliases": ["Patna", "पटना", "పాట్నా"],
        "coverage_tier": "B",
    },
    {
        "id": "UBL",
        "name": "SSS Hubballi Junction",
        "state": "Karnataka",
        "district": "Dharwad",
        "place_type": "station",
        "station_code": "UBL",
        "city_name": "Hubli",
        "lat": 15.3444,
        "lon": 75.1472,
        "aliases": ["Hubli", "Hubballi", "हुबली", "హుబ్లీ"],
        "coverage_tier": "B",
    },
    {
        "id": "COK",
        "name": "Cochin / Ernakulam Junction",
        "state": "Kerala",
        "district": "Ernakulam",
        "place_type": "station",
        "station_code": "ERS",
        "city_name": "Kochi",
        "lat": 9.9678,
        "lon": 76.2872,
        "aliases": ["Kochi", "Kochy", "Cochin", "Ernakulam", "కొచ్చి", "कोच्चि"],

        "coverage_tier": "B",
    },
    {
        "id": "BRC",
        "name": "Vadodara Junction",
        "state": "Gujarat",
        "district": "Vadodara",
        "place_type": "station",
        "station_code": "BRC",
        "city_name": "Vadodara",
        "lat": 22.3106,
        "lon": 73.1812,
        "aliases": ["Baroda", "Vadodara", "बड़ौदा", "వడోదర"],
        "coverage_tier": "B",
    },
    {
        "id": "TVC",
        "name": "Thiruvananthapuram Central",
        "state": "Kerala",
        "district": "Thiruvananthapuram",
        "place_type": "station",
        "station_code": "TVC",
        "city_name": "Thiruvananthapuram",
        "lat": 8.4875,
        "lon": 76.9525,
        "aliases": ["Trivandrum", "Thiruvananthapuram", "త్రివేండ్రం", "त्रिवेंद्रम"],
        "coverage_tier": "B",
    },
]


class Gazetteer:
    """In-memory indexed gazetteer for rapid search, alias resolution, and station code mapping."""

    def __init__(self, db: Session | None = None) -> None:
        self._places_by_id: dict[str, Place] = {}
        self._places_by_code: dict[str, Place] = {}
        self._alias_map: dict[str, Place] = {}  # Normalized lower alias -> Place
        self._load_default_places()
        if db:
            self.load_from_db(db)

    def _load_default_places(self) -> None:
        """Load default pan-India curated dictionary into internal lookup structures."""
        for p in DEFAULT_PLACES:
            place = Place(
                id=p["id"],
                name=p["name"],
                state=p["state"],
                district=p.get("district"),
                place_type=p.get("place_type", "station"),
                station_code=p.get("station_code"),
                city_name=p.get("city_name"),
                lat=p.get("lat", 0.0),
                lon=p.get("lon", 0.0),
                aliases=p.get("aliases", []),
                member_station_codes=p.get("member_station_codes", []),
                is_ambiguous=p.get("is_ambiguous", False),
                coverage_tier=p.get("coverage_tier", "B"),
            )
            self._register_place(place)

    def _register_place(self, place: Place) -> None:
        self._places_by_id[place.id] = place
        if place.station_code:
            self._places_by_code[place.station_code.upper()] = place

        # Map name itself
        self._alias_map[place.name.lower().strip()] = place

        # Map station code
        if place.station_code:
            self._alias_map[place.station_code.lower().strip()] = place

        # Map aliases
        for a in place.aliases:
            self._alias_map[a.lower().strip()] = place

    def load_from_db(self, db: Session) -> None:
        """Augment gazetteer with stations and aliases stored in database."""
        try:
            stations = db.query(Station).all()
            for st in stations:
                if st.code not in self._places_by_code:
                    place = Place(
                        id=st.code,
                        name=st.name,
                        state=st.city.state if st.city else "India",
                        district=st.city.district if st.city else None,
                        place_type=st.type,
                        station_code=st.code,
                        city_name=st.city.name if st.city else None,
                        lat=st.lat,
                        lon=st.lon,
                        coverage_tier="A" if st.code in ("BZA", "DMM", "HUP", "ATP") else "B",
                    )
                    self._register_place(place)

            aliases = db.query(Alias).all()
            for al in aliases:
                target_code: str | None = None
                if al.station_id:
                    matched_st: Station | None = db.query(Station).filter(Station.id == al.station_id).first()
                    if matched_st is not None:
                        target_code = matched_st.code
                elif al.city_id:
                    city: City | None = db.query(City).filter(City.id == al.city_id).first()
                    if city is not None:
                        # Find primary station for this city
                        primary_st: Station | None = db.query(Station).filter(Station.city_id == city.id).first()
                        if primary_st is not None:
                            target_code = primary_st.code

                if target_code and target_code in self._places_by_code:
                    self._alias_map[al.alias.lower().strip()] = self._places_by_code[target_code]
        except (OSError, RuntimeError) as err:
            structlog.get_logger("zero-friction-transit").warning("Failed to load places from db", error=str(err))


    def get_by_id(self, place_id: str) -> Place | None:
        return self._places_by_id.get(place_id)

    def get_by_code(self, code: str) -> Place | None:
        return self._places_by_code.get(code.upper().strip())

    def get_exact_by_alias(self, text: str) -> Place | None:
        clean = text.lower().strip()
        return self._alias_map.get(clean)

    def all_places(self) -> list[Place]:
        return list(self._places_by_id.values())

    def all_alias_keys(self) -> list[str]:
        return list(self._alias_map.keys())


# Global gazetteer singleton
default_gazetteer = Gazetteer()

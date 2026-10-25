"""Comprehensive test suite for Gazetteer, Fuzzy Matching, and Disambiguation (>= 60 cases)."""

import pytest

from app.places.disambiguate import default_disambiguator
from app.places.matching import default_matcher


# ==============================================================================
# 1. TYPO RESOLUTION (16 cases)
# ==============================================================================
@pytest.mark.parametrize(
    ("typo_input", "expected_code"),
    [
        ("Dharmavram", "DMM"),
        ("Vjayawada", "BZA"),
        ("Secundrabad", "SC"),
        ("Hydrabad", "CITY_HYDERABAD"),
        ("Banglore", "CITY_BLR"),
        ("Tirupathi", "TPTY"),
        ("Hindupoor", "HUP"),
        ("Chenai", "CITY_CHENNAI"),
        ("Anantpur", "ATP"),
        ("Guntoor", "GNT"),
        ("Guntkal", "GTL"),
        ("Howra", "HWH"),
        ("Kochy", "ERS"),
        ("Vadodra", "BRC"),
        ("Trivandram", "TVC"),
        ("Visakapatnam", "VSKP"),
    ],
)
def test_typo_fuzzy_matching(typo_input: str, expected_code: str) -> None:
    match = default_matcher.match(typo_input)
    assert match is not None, f"Expected match for typo '{typo_input}'"
    assert match.score >= 80.0
    actual_id = match.place.station_code or match.place.id
    assert actual_id == expected_code or match.place.id == expected_code


# ==============================================================================
# 2. STATION CODES (12 cases)
# ==============================================================================
@pytest.mark.parametrize(
    ("station_code", "expected_name"),
    [
        ("BZA", "Vijayawada Junction"),
        ("DMM", "Dharmavaram Junction"),
        ("HUP", "Hindupur Railway Station"),
        ("ATP", "Anantapur Railway Station"),
        ("SC", "Secunderabad Junction"),
        ("HYB", "Hyderabad Deccan (Nampally)"),
        ("TPTY", "Tirupati Main"),
        ("SBC", "KSR Bengaluru City Junction"),
        ("MAS", "Chennai Central"),
        ("NDLS", "New Delhi Railway Station"),
        ("CSMT", "Chhatrapati Shivaji Maharaj Terminus"),
        ("VGA", "Vijayawada International Airport"),
    ],
)
def test_station_code_exact_lookup(station_code: str, expected_name: str) -> None:
    match = default_matcher.match(station_code)
    assert match is not None
    assert match.match_type == "exact_code"
    assert match.score == 100.0
    assert match.place.name == expected_name


# ==============================================================================
# 3. HINDI SPELLINGS (10 cases)
# ==============================================================================
@pytest.mark.parametrize(
    ("hindi_input", "expected_id"),
    [
        ("विजयवाड़ा", "BZA"),
        ("धर्मवरम", "DMM"),
        ("हैदराबाद", "CITY_HYDERABAD"),
        ("सिकंदराबाद", "SC"),
        ("तिरुपति", "TPTY"),
        ("बेंगलुरु", "CITY_BLR"),
        ("चेन्नई", "CITY_CHENNAI"),
        ("मद्रास", "CITY_CHENNAI"),
        ("नई दिल्ली", "NDLS"),
        ("मुंबई", "CSMT"),
    ],
)
def test_hindi_spellings(hindi_input: str, expected_id: str) -> None:
    match = default_matcher.match(hindi_input)
    assert match is not None, f"Hindi spelling '{hindi_input}' must be recognized"
    assert match.place.id == expected_id or match.place.station_code == expected_id


# ==============================================================================
# 4. TELUGU SPELLINGS (11 cases)
# ==============================================================================
@pytest.mark.parametrize(
    ("telugu_input", "expected_id"),
    [
        ("విజయవాడ", "BZA"),
        ("ధర్మవరం", "DMM"),
        ("హిందూపురం", "HUP"),
        ("అనంతపురం", "ATP"),
        ("గుంటూరు", "GNT"),
        ("అమరావతి", "CITY_AMARAVATI"),
        ("హైదరాబాద్", "CITY_HYDERABAD"),
        ("సికింద్రాబాద్", "SC"),
        ("తిరుపతి", "TPTY"),
        ("బెంగళూరు", "CITY_BLR"),
        ("విశాఖపట్నం", "VSKP"),
    ],
)
def test_telugu_spellings(telugu_input: str, expected_id: str) -> None:
    match = default_matcher.match(telugu_input)
    assert match is not None, f"Telugu spelling '{telugu_input}' must be recognized"
    assert match.place.id == expected_id or match.place.station_code == expected_id


# ==============================================================================
# 5. DUPLICATE NAMES & DISAMBIGUATION (8 cases)
# ==============================================================================
def test_aurangabad_ambiguity_prompt() -> None:
    """Bare 'Aurangabad' must trigger disambiguation between Maharashtra and Bihar."""
    res = default_disambiguator.resolve("Aurangabad")
    assert res.is_ambiguous is True
    assert len(res.candidates) >= 2
    states = [c.state for c in res.candidates]
    assert "Maharashtra" in states
    assert "Bihar" in states


def test_bilaspur_ambiguity_prompt() -> None:
    """Bare 'Bilaspur' must trigger disambiguation between CG and HP."""
    res = default_disambiguator.resolve("Bilaspur")
    assert res.is_ambiguous is True
    assert len(res.candidates) >= 2
    states = [c.state for c in res.candidates]
    assert "Chhattisgarh" in states
    assert "Himachal Pradesh" in states


def test_rampur_ambiguity_prompt() -> None:
    """Bare 'Rampur' must trigger disambiguation between UP and Bihar."""
    res = default_disambiguator.resolve("Rampur")
    assert res.is_ambiguous is True
    assert len(res.candidates) >= 2


def test_aurangabad_maharashtra_unambiguous() -> None:
    """Qualified 'Aurangabad Maharashtra' should resolve directly to AWB."""
    res = default_disambiguator.resolve("Aurangabad Maharashtra")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.station_code == "AWB"
    assert res.resolved_place.state == "Maharashtra"


def test_aurangabad_bihar_unambiguous() -> None:
    """Qualified 'Aurangabad Bihar' should resolve directly to AUBR."""
    res = default_disambiguator.resolve("Aurangabad Bihar")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.station_code == "AUBR"
    assert res.resolved_place.state == "Bihar"


def test_bilaspur_cg_unambiguous() -> None:
    res = default_disambiguator.resolve("Bilaspur CG")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.station_code == "BSP"


def test_bilaspur_hp_unambiguous() -> None:
    res = default_disambiguator.resolve("Bilaspur HP")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.state == "Himachal Pradesh"


def test_rampur_up_unambiguous() -> None:
    res = default_disambiguator.resolve("Rampur UP")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.station_code == "RMFO"


# ==============================================================================
# 6. MULTI-STATION CITY CLUSTERS (6 cases)
# ==============================================================================
def test_hyderabad_city_cluster_expansion() -> None:
    res = default_disambiguator.resolve("Hyderabad")
    assert res.is_ambiguous is False
    assert "SC" in res.member_stations
    assert "HYB" in res.member_stations
    assert "KCG" in res.member_stations


def test_secunderabad_direct_station() -> None:
    res = default_disambiguator.resolve("Secunderabad")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.station_code == "SC"


def test_bengaluru_city_cluster_expansion() -> None:
    res = default_disambiguator.resolve("Bengaluru")
    assert res.is_ambiguous is False
    assert "SBC" in res.member_stations
    assert "YPR" in res.member_stations


def test_chennai_city_cluster_expansion() -> None:
    res = default_disambiguator.resolve("Chennai")
    assert res.is_ambiguous is False
    assert "MAS" in res.member_stations
    assert "MS" in res.member_stations


def test_amaravati_city_cluster() -> None:
    res = default_disambiguator.resolve("Amaravati")
    assert res.is_ambiguous is False
    assert "BZA" in res.member_stations


def test_vijayawada_direct_node() -> None:
    res = default_disambiguator.resolve("Vijayawada")
    assert res.is_ambiguous is False
    assert res.resolved_place is not None
    assert res.resolved_place.station_code == "BZA"


# ==============================================================================
# 7. UNKNOWN & FICTITIOUS PLACES RETURN NONE (8 cases)
# ==============================================================================
@pytest.mark.parametrize(
    "fake_place",
    [
        "Atlantis",
        "Hogwarts",
        "Gotham City",
        "Mordor",
        "Narnia",
        "Wakanda",
        "Xyzqwerty999",
        "Randomgibberishplace",
    ],
)
def test_unknown_place_returns_none(fake_place: str) -> None:
    """Anti-hallucination guarantee: Unrecognized places MUST NOT resolve to arbitrary stations."""
    match = default_matcher.match(fake_place)
    assert match is None, f"Fake place '{fake_place}' must return None"

    res = default_disambiguator.resolve(fake_place)
    assert res.resolved_place is None
    assert res.is_ambiguous is False

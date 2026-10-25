# Interactive Demo Script & Evaluator Walkthrough

This script provides 5 verified query paths for live demonstration and automated end-to-end evaluation.

---

## Query 1: The Core Student Commute (Demo Corridor)
- **Prompt**: `"Find me a combined train and bus route home from Vijayawada to Dharmavaram for Friday evening under ₹800"`
- **Expected Parser Interpretation**:
  - Origin: Vijayawada (BZA)
  - Destination: Dharmavaram (DMM)
  - Date: Upcoming Friday
  - Window: 16:00 - 21:00 (Evening)
  - Budget: Max ₹800
- **Expected Result**:
  - Direct & Multi-leg train + bus connections via Guntakal or Anantapur.
  - Truth Badges: `COMMUNITY_GTFS` / `OFFICIAL_TIMETABLE`.
  - Leg timeline rendered with proportional durations and layover indicators.
  - Price within ₹800.

---

## Query 2: Fast Intercity Rail & Air (Tier B Corridor)
- **Prompt**: `"Hyderabad to Chennai tomorrow night, AC only"`
- **Expected Parser Interpretation**:
  - Origin: Hyderabad / Secunderabad
  - Destination: Chennai Central / Egmore
  - Class: AC (3A, 2A, 1A, CC)
  - Window: Night (20:00 - 04:00)
- **Expected Result**:
  - Overnight express trains (e.g. Charminar Exp) + connecting options.

---

## Query 3: Multi-Station City & Ambiguity Resolution
- **Prompt**: `"Aurangabad to Tirupati next Monday morning"`
- **Expected Behavior**:
  - Ambiguity prompt asks user to clarify between Aurangabad (Maharashtra - AWB) vs Aurangabad (Bihar).
  - One-tap selection instantly triggers search without re-typing.

---

## Query 4: Unverified Fare & NULL-Safe Budget Handling
- **Prompt**: `"Hindupur to Guntur under ₹400 with bus and train"`
- **Expected Behavior**:
  - If a bus leg has an unverified community fare, the overall itinerary cost displays as `"₹220 + 1 leg fare unknown"`.
  - Filter marks card as `"Budget unverified"`, strictly avoiding treating unknown fares as zero.

---

## Query 5: LLM Offline / Basic Mode
- **Prompt**: `"Kacheguda to Tirupati 15 November Sleeper"`
- **Expected Behavior**:
  - Pure deterministic regex & dateparser engine successfully extracts all parameters in $< 50\text{ms}$.
  - UI displays the **Basic Mode** badge confirming zero external LLM dependence.

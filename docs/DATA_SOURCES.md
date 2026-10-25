# Data Sources, Truth Levels, and Freshness Policy

## 1. Principle: Real Data & Honest Badges

No synthetic hallucinations of transport routes or schedules are ever displayed as real data. When data is unavailable, it is marked as `UNKNOWN` or `Fare unavailable`.

### Truth Levels
1. **`OFFICIAL_TIMETABLE`**: Sourced directly from official Railway Board publications or transport corporation schedules.
2. **`COMMUNITY_GTFS`**: Sourced from community-verified GTFS transit feeds (e.g., MobilityDatabase).
3. **`LIVE_API`**: Fetched dynamically within TTL from an authorized transit or aviation API.
4. **`ESTIMATED`**: Derived from documented fare rules (e.g., standard telescopic rail fare slabs) or geographic transfer estimates.
5. **`USER_PROVIDED`**: Sourced from user input during the active session (e.g., "I see WL 12 on IRCTC").
6. **`UNKNOWN`**: Data missing or unverified. Never defaulted to 0 or arbitrary numbers.

---

## 2. Configured Providers

| Provider ID | Mode | Truth Level | Source / License | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `gtfs_rail` | Rail | `COMMUNITY_GTFS` | Open Data / ODbL | Indian Railways community GTFS |
| `gtfs_bus_apsrtc` | Bus | `COMMUNITY_GTFS` | Open Data / CC-BY | APSRTC regional bus network |
| `official_rail` | Rail | `OFFICIAL_TIMETABLE` | Railway Board ("Trains at a Glance") | Local timetable importer |
| `datameet_rail` | Rail | `OFFICIAL_TIMETABLE` | DataMeet (CC0) | Station coordinates & names |
| `flights_airlabs` | Flight | `LIVE_API` | AirLabs API | Schedules & status |
| `fares_estimated` | All | `ESTIMATED` | `fares.yaml` | Distance-based telescopic formulas |
| `user_provided` | All | `USER_PROVIDED` | User session | Session overrides |

---

## 3. Freshness & Validation Rules
- **Calendar Expiry**: Feeds whose calendar `end_date` is earlier than the travel date produce an explicit banner: `"Schedule data expired on <date>"`.
- **Validation Rejects**: Corrupted stop times, negative durations, or impossible velocities are logged to `data/rejects.csv` and excluded from routing tables.

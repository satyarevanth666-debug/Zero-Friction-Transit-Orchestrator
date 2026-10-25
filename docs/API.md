# API Specifications (`/api`)

All endpoints return JSON unless explicitly streaming (SSE). All responses include `request_id`.

## 1. Planning & Search

### `POST /api/plan` (Server-Sent Events)
Streamed itinerary generation.
- **Payload**:
  ```json
  {
    "query": "Find me a combined train and bus route home for Friday evening under ₹800",
    "overrides": {
      "budget": 800,
      "date": "2026-10-30"
    }
  }
  ```
- **Stream Events**:
  1. `event: parsing` -> `{"status": "parsing", "query": "..."}`
  2. `event: intent` -> `{"intent": { "origin": "...", "destination": "...", ... }}`
  3. `event: resolving` -> `{"status": "resolved_places", "candidates": [...]}`
  4. `event: planning` -> `{"status": "running_raptor", "rounds": 3}`
  5. `event: ranking` -> `{"status": "ranked", "count": 5}`
  6. `event: explaining` -> `{"status": "generating_explanations"}`
  7. `event: results` -> Full ItineraryResponse JSON payload
  8. `event: done` -> `{"status": "completed"}`

### `POST /api/plan/sync`
Synchronous JSON equivalent of `/api/plan` for programmatic calls and automated tests.

### `GET /api/places?q={search}`
Autocomplete endpoint for cities, stations, bus stands, and airports. Returns type, state, aliases, and distance if geo-coordinates provided.

### `GET /api/coverage?from={origin}&to={destination}`
Coverage tier summary (`tier`: A | B | C) indicating available data sources and live providers.

### `GET /api/data-status`
Returns inventory of all registered transit providers, dataset freshness, calendar validity dates, licenses, and row counts.

### `GET /api/health`
Health check endpoint returning system status and provider connectivity.

---

## 2. Authentication & Profile

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/change-password`
- `GET /api/auth/me`
- `DELETE /api/auth/account`

---

## 3. Trips & Preferences
- `GET /api/trips` - List saved itineraries
- `POST /api/trips` - Save itinerary
- `DELETE /api/trips/{id}` - Delete saved itinerary
- `GET /api/me/places` - Get custom saved locations (Home, College)
- `POST /api/me/places` - Upsert custom saved location

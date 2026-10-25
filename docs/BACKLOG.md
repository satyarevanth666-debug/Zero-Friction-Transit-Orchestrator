# Project Backlog & Roadmap

This backlog tracks pending enhancements, external API integrations, future phases, and any code TODOs across the Zero-Friction Transit Orchestrator codebase.

---

## 1. External Providers & Integrations (Pending User Credentials/Confirmations)
- [ ] **Third-Party Real-Time Rail API**
  - **Description**: Enable live PNR, train running status, and live seat availability queries via third-party provider once credentials and Terms of Service are reviewed and approved.
  - **Flag**: `ENABLE_THIRD_PARTY_RAIL=true`
  - **Action Needed**: Review provider terms and configure `RAIL_API_KEY`.
- [ ] **Official Railway Timetable ("Trains at a Glance") File Import**
  - **Description**: Ingestion pipeline for official Railway Board timetable publication once source PDF/CSV is placed in `data/raw/`.
  - **Action Needed**: User to provide verified official timetable source file.
- [ ] **Live Flight Provider API**
  - **Description**: Pluggable adapter for live flight status and schedules (AirLabs / AeroDataBox).
  - **Flag**: `FLIGHT_PROVIDER=airlabs`, `FLIGHT_API_KEY=...`
  - **Action Needed**: User to provide API key and confirm free tier limits.
- [ ] **Production SMTP Mailer**
  - **Description**: Switch from dev in-memory/console mailer to production SMTP server.
  - **Flag**: Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`.
- [ ] **Google OAuth SSO**
  - **Description**: Pluggable one-tap Google login using Authlib.
  - **Flag**: `ENABLE_GOOGLE_OAUTH=true`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

---

## 2. Transit Engine Enhancements (Post-MVP)
- [ ] **Multi-City Metro Feeds**: Add GTFS ingestion for Hyderabad Metro, Chennai Metro, and Bengaluru Namma Metro for automated first-mile / last-mile transfers.
- [ ] **Dynamic Delay Prediction**: Historical delay patterns by train number and season.
- [ ] **User-Reported Availability Verification**: Peer upvoting and verification threshold for user-reported WL positions.

---

## 3. Codebase TODOs & Technical Debt
*(No active unaddressed TODOs in core production modules; all design requirements follow Section 0 and are tracked here).*

# Authentication & Security Architecture

## 1. Security Overview

Zero-Friction Transit implements defense-in-depth for guest and authenticated sessions:
- **Guest Access**: Full search, multimodal itinerary generation, and data source inspection require zero authentication.
- **Authenticated Access**: Saving trips, viewing search history, setting saved places (Home/College), and personal transit preferences require an account.

---

## 2. Token Life-Cycle & Cookie Security

| Token | Validity | Storage | Flags | Rotation Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Access Token (JWT)** | 15 minutes | HTTP-Only Cookie (`access_token`) | `HttpOnly`, `SameSite=Lax`, `Secure` (prod), `Path=/` | Reissued via refresh |
| **Refresh Token (Opaque Hash)** | 7 days | HTTP-Only Cookie (`refresh_token`) | `HttpOnly`, `SameSite=Lax`, `Secure` (prod), `Path=/api/auth` | **Strict rotation on every use**; old token revoked immediately |
| **CSRF Token** | 1 session | Cookie (`csrf_token`) & Header (`X-CSRF-Token`) | Readable by JS, checked on all state-changing endpoints (POST/PUT/DELETE) | Double-submit cookie verification |

---

## 3. Password Storage & Policies
- **Hashing Algorithm**: Argon2id (`argon2-cffi`) with custom memory and parallelism parameters exceeding OWASP recommendations.
- **Constraints**: Minimum 10 characters. Checked against common password dictionaries.
- **Timing Attack Mitigation**: Login verification returns generic `Email or password is incorrect` with identical response timing whether the email exists or not.
- **Password Reset**: Single-use cryptographic tokens with a 30-minute expiration window.

---

## 4. Rate Limiting (SlowAPI)
- `POST /api/auth/login`: 5 requests per minute per (IP + email).
- `POST /api/plan`: 20 requests per minute per IP.
- Responses on breach: `429 Too Many Requests` with `Retry-After` header.

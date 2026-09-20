# Backend foundation and authentication

Phase 05 uses `create_app(settings, database_engine)` with `/api/v1` routers, typed environment settings, request-scoped SQLAlchemy sessions and dependency injection. Routes delegate registration, login, session checks and throttling to services. No generic repository layer is needed for these small operations. Models remain in `app/models`, request/response contracts in `app/schemas`, and security/error primitives in `app/core`. `app/db.py` remains a focused module rather than an empty folder hierarchy.

## API contract

| Method and route | Behavior |
| --- | --- |
| GET `/api/v1/health` | Process liveness, no database connection |
| GET `/api/v1/ready` | PostgreSQL query, safe 503 on failure |
| GET `/api/v1/auth/csrf` | Obtain a pre-login CSRF token/cookie, or refresh the signed-in session's CSRF token |
| POST `/api/v1/auth/register` | Email, name, password; creates a customer and returns a public user, HTTP 201 |
| POST `/api/v1/auth/login` | Email/password; returns public user and CSRF token; sets HTTP-only session cookie |
| GET `/api/v1/auth/me` | Signed-in active user only |
| GET `/api/v1/auth/admin` | Signed-in active administrator only; demonstrates the reusable role dependency |
| POST `/api/v1/auth/logout` | Requires session CSRF token; deletes session server-side and expires cookie, HTTP 204 |

Fetch `/auth/csrf` before registration/login with same-origin credentials. Retain its returned `csrf_token` in memory and submit it as `X-CSRF-Token`; the matching signed HTTP-only pre-auth cookie is sent by the browser. After login, use the new session-bound token in the login response for authenticated writes. Obtain another token through `/auth/csrf` after a page reload. Refreshing the token invalidates previously returned session CSRF tokens, so callers must replace stale values and retry only after a fresh token when they receive `invalid_csrf`.

Requests to CSRF issuance and state-changing auth endpoints must carry an allowed Origin or an exact-origin Referer. Browsers supply these headers; programmatic clients must set Origin themselves. Missing provenance is rejected. Never set permissive CORS to bypass these checks. Registration does not automatically log in. Swagger displays schemas, but a programmatic or frontend client is needed for the complete cookie/CSRF sequence.

Public errors use `{"error":{"code":"...","message":"..."},"request_id":"..."}`. Common codes: invalid_input (422), email_registered (409), invalid_credentials/unauthorized (401), forbidden/invalid_origin/invalid_csrf (403), rate_limited (429), database_unavailable (503). Validation errors intentionally omit raw input/context to prevent password reflection. Duplicate email registration is explicitly identified as requested; this reveals account existence, mitigated by throttling. Login always uses the same generic error for unknown, incorrect or disabled accounts.

## Security behavior

- Passwords use Argon2id (64 MiB memory, 3 iterations, parallelism 2), random salts and rehash-on-login. Registration accepts 15–128-character passphrases, rejects highly repetitive values and a small explicit common-password list. This list is not a breached-password database; stronger breach screening is a later hardening task. Passwords are never returned, logged or silently trimmed.
- Emails are validated and normalized to lowercase with a database uniqueness constraint. Public registration forbids extra fields, including role/status. Accounts are active or disabled; every session check reloads account state and permissions.
- Random 256-bit opaque session tokens are stored only as SHA-256 hashes. Cookies are HTTP-only, host-only, Path=/ and SameSite=Lax. Production adds Secure and a `__Host-` cookie name; deletion uses matching secure attributes. No JWT or browser localStorage token is used.
- Customers: 7-day absolute/24-hour idle expiry. Admins: 8-hour absolute/30-minute idle expiry. Database checks enforce expiration, including the current role's shorter limit. Logout revokes the database session, so replaying the old cookie fails. Changing a role/status should also revoke sessions operationally; there is no public role-management endpoint.
- Pre-auth CSRF cookies are random, timestamped and HMAC-signed, valid for 10 minutes. Authenticated CSRF values are tied to the session through a stored hash. CORS accepts exact configured origins only and credentials, GET/POST, Content-Type and X-CSRF-Token.
- PostgreSQL rate buckets atomically count attempts across processes. Login is capped at 10 attempts per normalized email per 15 minutes; registration/login share 50 attempts per peer IP per 15 minutes by default. Counters commit even on login failure. Keys are HMACs, not raw emails/IPs. `cleanup-auth` removes expired buckets/sessions.
- The IP limit uses the ASGI peer address. Production ingress must sanitize forwarded headers and configure Uvicorn's trusted proxies narrowly. With the development Next.js proxy, clients may share its loopback address; do not blindly trust arbitrary X-Forwarded-For to solve that. An ingress rate limit remains a deployment requirement.
- Auth responses are `no-store`. Request bodies are bounded to 16 KiB for current write endpoints. Future media uploads need a separate bounded upload path. Logs contain generated request ID, method, status and timing; no request bodies, credentials, query strings or raw SQL errors. Unexpected errors return safe 500 messages.

## Administration and deployment settings

Run `python -m app.cli create-admin` through the backend virtualenv. Password input is hidden and repeated; it never promotes an existing customer automatically. There are no seeded/default administrator credentials. Run `python -m app.cli cleanup-auth` daily through the deployment scheduler. No scheduler is installed now.

Set `APP_ENV=production`, an independently generated `AUTH_SECRET` of at least 32 characters, a non-development `DATABASE_URL` and exact HTTPS `ALLOWED_ORIGINS` before deploying. Startup rejects insecure production defaults. Keep these values outside Git. `SESSION_HOURS`, `IDLE_MINUTES`, `ADMIN_SESSION_HOURS` and `ADMIN_IDLE_MINUTES` can be changed within validated bounds. API docs are disabled in production. TLS/ingress and hosting are later phases.

This phase implements customer/admin credential authentication and role enforcement. Email verification, password recovery, admin MFA, breached-password screening, security review and full production hardening remain required before launch. Social login is deliberately absent. These backend endpoints do not constitute finished login/account pages.

## Verification

The integration suite runs against real PostgreSQL with the Alembic migration, not SQLite or an in-memory substitute. It covers all eight requested auth scenarios plus disabled accounts, expiry, role injection, CSRF/origin checks, body limits, CORS, throttling and production cookie attributes. Database tests cover money, inventory, foreign keys, transitions, immutable snapshots and append-only audit history. Fixtures isolate rows using outer transactions/savepoints. CI explicitly supplies a disposable `_test` database; skipped integration tests must not be reported as passed.

Security design references: [OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), and [CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). Deployment-specific review is still necessary.

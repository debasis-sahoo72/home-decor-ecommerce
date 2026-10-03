# Automated testing strategy — Prompt 25

This strategy tests customer and operator outcomes: correct prices, stock, ownership, payment state and usable recovery from failures. It does not treat test counts, snapshots or code coverage percentages as proof of correctness.

## Current implementation and boundaries

| Layer | Current automation | Boundary |
| --- | --- | --- |
| Backend unit/API/database | Pytest, real PostgreSQL, Alembic migrations, transaction-isolated fixtures | FastAPI TestClient; not a real network/browser deployment |
| Cross-feature journeys | `backend/tests/test_customer_journey.py` | Browse → guest bag → login merge → checkout → captured/unpaid outcomes → admin fulfilment, with a fake provider |
| Frontend logic/contracts | Node test runner: SEO/JSON-LD and shopping request behavior | No DOM rendering or browser interaction |
| SEO HTTP smoke | `frontend/scripts/check-seo.mjs` | Running frontend/backend, metadata/status/redirect/robots checks |
| Browser components and full E2E | **Specified below; not implemented yet** | Required before launch, including mobile and actual browser interaction |
| Razorpay sandbox integration | **Not implemented yet** | Deferred until merchant/test-mode integration is finalized; never claim fake-provider tests verify Razorpay |

No browser testing dependency is added merely to document this strategy. Use Playwright for the browser layer when implementing it; it can exercise both focused interactive components through real pages and complete journeys. Avoid adding a separate component runner unless browser tests become too slow or an isolated component has substantial business behavior. Next.js server components should be exercised through rendered routes rather than mocked React internals.

## Backend coverage matrix

| Area / existing suites | Required business assertions and negative cases |
| --- | --- |
| Unit: delivery, operations, config | Exact cutoff/timezone boundaries; current calendar-day policy includes weekends/holidays; every allowed/rejected order transition; insecure production defaults rejected |
| API foundation: health, config, auth | Liveness independent of DB; readiness unavailable safely; invalid/oversized input; no password/raw SQL/provider error leakage; no-store on private responses |
| Database: database and migration suites | Foreign keys, unique email/slug/SKU, Decimal money, positive quantities, nonnegative available stock, immutable financial snapshots, append-only audit events, migration upgrade/downgrade on disposable DB |
| Authentication: auth | Registration, duplicate account, valid/invalid login, disabled account, expiry, logout replay, cookie flags, CSRF/origin rejection, password limits, durable rate limits |
| Authorization: addresses, cart_wishlist, operations, media, reviews | Anonymous 401; customer denied admin; cross-customer IDs return no data; writes require CSRF; ownership applies to reads, edits, deletes and defaults |
| Products: catalog, offers, demo_catalog | Public visibility, valid slugs, duplicate rejection, filters/sort/page bounds, discounted variants only in Offers, exact prices, genuine ratings only, inactive products unavailable |
| Cart/wishlist: shopping, cart_wishlist | Guest persistence and isolation, login merge, add/update/remove/clear, server totals, duplicates, invalid IDs, zero/negative/fractional/boolean quantities, quantity over stock, inactive/deleted products |
| Addresses | Required fields, India PIN/phone validation, default replacement, address limit, other customer's address rejected at checkout |
| Delivery: delivery and delivery_migration | Bangalore standard service, other approved urban PIN, unknown/inactive/rural PIN unavailable, malformed PIN rejected, fee and date calculation |
| Checkout: checkout | Price/address/serviceability changes after quote; server stock checks; same idempotency key creates one order; changed payload conflicts; payment unavailable; stock reservation/cancel behavior |
| Payments: checkout | Captured status only; wrong amount/currency/order/payment status/refund rejected; duplicate confirm/webhook safe; bad signature; timeout ambiguity cannot create another provider order; no browser-trusted success |
| Orders/admin: operations | Customer list/details/status, admin search/filter, valid fulfilment sequence, stale/invalid transitions, customer admin denial, manual paid/refunded status denied, stock adjustment once |
| Media/reviews/notifications | Image content/size/pixel limits; cross-product image IDs; purchase eligibility and moderation; deduplicated events; opt-out; provider failures isolated from order commit; no sensitive payloads |

Cross-feature journey tests supplement these focused tests; they do not replace edge-case coverage. Fake payment providers represent captured, uncaptured, mismatch and ambiguous outcomes. Use HTTP transport mocks to test provider request/response contracts separately, and a sandbox to verify the actual provider contract.

## Frontend behavior tests

Current request tests check that expired sessions prevent a mutation, stock errors reach the shopper, a later action recovers after failure, proxy HTML errors become useful messages, deletion accepts an empty 204 response, and a network failure does not automatically replay order creation.

The planned browser interaction suite should test:

| Surface | Positive path | Negative/recovery path |
| --- | --- | --- |
| Header/navigation | Shop, Offers, search and category links; cart/wishlist counts update | API outage has a visible recoverable error; no false zero count treated as success |
| Product | Choose variant/quantity; change gallery image; save item | Out-of-stock/invalid quantity blocks action; serviceability unavailable never promises delivery |
| Cart | Change quantity, remove, clear, refresh persistence | Server stock rejection preserves understandable state; double-click does not create unintended quantity |
| Wishlist | Toggle and add to cart; login merge | Inactive item and network failure handled; duplicates prevented |
| Login/register | Correct credentials navigate to allowed destination | Empty/invalid email and short password show validation; server rejection visible; arbitrary `next` URL not followed |
| Address form | Add/edit/default/delete and select at checkout | Missing required fields, invalid PIN/phone, rejected ownership and server failure preserve editable form |
| Checkout | Select address, review quote, initiate once, display verified order | No serviceability, changed price/stock, failed payment, closed window, timeout, reload, repeated submit and stale session |
| Admin orders | Filter/find order and apply valid transition with reason | Customer cannot use admin APIs; stale transition refreshes rather than overwriting newer state |

Assert visible labels, roles, URLs, amounts and order states. Use `getByRole`/`getByLabel`; avoid CSS class names, React state, private function calls and broad HTML snapshots. Test keyboard operation and a narrow mobile viewport on checkout/address/cart. Use targeted accessibility assertions for labels, focus and error announcements.

## End-to-end acceptance scenarios

These are executable-suite specifications, **not claims that browser tests already exist**. Automate with real Next.js + FastAPI + PostgreSQL and fake only external providers. A browser route mock of the entire backend is a UI test, not full E2E.

1. **Browse product:** homepage → category/search → product detail. Assert correct product/variant/price, gallery and meaningful alt text. Negative: unknown slug gives 404; inactive product cannot be purchased.
2. **Add to cart:** add as guest, see count and totals, reload, change quantity, remove. Sign in and verify merge without duplicate lines. Negative: attempt stock + 1; server rejects and UI shows the reason.
3. **Checkout:** sign in, add/select owned address, check PIN, review server totals. Negative: unserviceable PIN, another customer's address ID, stale price/stock, expired session; no payable order is created from invalid input.
4. **Payment success:** create one provider order, simulate external capture in the test adapter, confirm through the real backend, display confirmed order, clear purchased cart quantities and consume stock once. Repeat browser callback and signed webhook; assert one order and one capture transition.
5. **Payment failure:** declined/uncaptured response leaves the order pending and never shows paid confirmation or fulfils stock. Closing the window preserves resumable state. An ambiguous timeout must not create a second payment attempt; a browser success callback alone cannot mark the order paid.
6. **Order creation/recovery:** double-submit/reload with the same idempotency key; exactly one order. A changed quote/address with that key conflicts. Another customer cannot read, confirm or cancel it.
7. **Admin management:** a separately authenticated administrator finds the captured order, moves through processing/packed/shipped/out-for-delivery/delivered, and sees an audit trail. Invalid jumps, stale expected states and customer requests are rejected; customer sees updated status without internal audit details.

Run all seven on desktop Chromium per PR once the suite exists. Run critical cart/checkout/address paths at a mobile viewport per PR. Add Firefox/WebKit to scheduled/pre-release runs rather than multiplying every test on every commit initially.

## Browser harness and safe data design

- Reserve dedicated ports (for example frontend 3100/backend 8100), a separate database ending `_test`, and explicit `APP_ENV=test`. Never attach tests to the existing preview or production database.
- Build Next.js for browser CI; configure `BACKEND_URL` before build and runtime, with exact test origins in backend settings. Keep indexing disabled.
- Fail setup if the test database is not explicitly supplied or the expected test origin/port is absent. CI must fail when database tests would otherwise skip.
- Seed synthetic users, a distinct administrator, two products/variants, known inventory and serviceable/nonserviceable PINs. Each scenario gets unique IDs/emails/SKUs; no real customer data, secrets or public demo reviews.
- Prefer a database/schema per worker. Start with one browser worker to avoid shared-inventory interference. Clean only the explicitly designated test database; never use unconditional destructive cleanup against `DATABASE_URL`.
- Load a fake provider through a **test-only launcher/dependency override**, not a public “mark paid” endpoint or production environment shortcut. Webhook tests still exercise signature validation. Block unexpected outbound provider calls; collect fake sends locally.
- Use separate browser contexts for guest, customer A, customer B and admin. Fixture code may provision roles directly; browser users must not be able to grant roles.
- Restore test state between cases; no dependence on test ordering. Freeze or inject dates at delivery/expiry boundaries. Use observable waits and Playwright assertions, not fixed sleeps.
- Retain traces/screenshots on failures only, using synthetic data. Never publish session cookies, provider credentials or real addresses in CI artifacts.

## Known audit findings and missing verification

Prompt 24 identified indefinite initiated-payment reservations, unverified WhatsApp recipients, registration enumeration and forwarded-IP trust. This testing work **does not fix those findings**. Ordinary green tests do not clear them.

For each fix, first add a failing regression expressing the desired secure behavior, then fix and make it pass. Do not encode the vulnerable outcome as a normal passing acceptance test, delete the assertion, or silently xfail a launch blocker. Keep audit reproductions separate from acceptance tests.

Outstanding tests before launch:

- Concurrent checkouts from separate connections for the last unit; no oversell or lost reservation.
- Concurrent capture/webhook/reconciliation, safe reservation expiry and late capture; exactly-once stock effects.
- Verified WhatsApp number enrollment, changed-number invalidation and recipient/account abuse limits.
- End-to-end proxy-header spoofing through the actual ingress; distinct real clients remain distinct.
- Uniform registration behavior once email verification is implemented.
- Browser scenarios above and real Razorpay test-mode success/failure/webhook reconciliation.
- Production-like backup restore, migration rollback/forward repair, TLS/cookie/security-header and ingress limits.

Do not add real card numbers or OTPs to fixtures. Sandbox payment tests are opt-in, use separate merchant credentials, are never run against live keys, and must not be required on untrusted fork PRs. Until sandbox tests run successfully, report the payment integration as mock-verified only.

## CI gates and failure policy

Existing CI runs backend pytest/ruff/migrations and frontend tests/lint/typecheck/contrast/build. The new tests are discovered by the existing commands. Pillow is now included in the Python lockfile so a clean test environment can import the media code. Missing `TEST_DATABASE_URL` now fails in CI rather than silently skipping integration tests.

Once browser automation is implemented, add a separate job with PostgreSQL, application startup/readiness, Chromium install and the critical suite. Use no retries locally and at most one diagnostic CI retry; a retry-only pass is a flake to investigate, not permission to ignore it. Quarantine requires an owner, issue and deadline and must not conceal payment/ownership/stock failures.

Required PR checks: all nonquarantined tests pass, no unexpected skips, lint/typecheck/build pass, migrations apply on a fresh database, no secrets in artifacts. Release additionally requires browser/sandbox and operational checks above. Track coverage of the business-risk matrix, not an arbitrary line-coverage target.

## Local VS Code commands (PowerShell)

PostgreSQL must already be running and `decor_test` must exist. These tests do not require the preview frontend/backend servers.

```powershell
cd C:\Users\sonal\Projects\home-decor-ecommerce\backend
$env:TEST_DATABASE_URL='postgresql+psycopg://decor:local-development-only@127.0.0.1:55432/decor_test'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Focused journey/payment checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_customer_journey.py tests/test_checkout.py -q
```

Frontend tests and build checks:

```powershell
cd C:\Users\sonal\Projects\home-decor-ecommerce\frontend
npm test
npm run lint
npm run typecheck
npm run build
```

If npm is unavailable, replace `npm` with `node ..\.tools\npm\package\bin\npm-cli.js`. For the existing SEO HTTP smoke check only, start the application first, then run `node scripts/check-seo.mjs`. There is intentionally no `test:e2e` command yet; do not report browser coverage until the harness and scenarios are implemented.

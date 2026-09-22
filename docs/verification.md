# Verification through phase 06

Executed locally on Windows with Node 24.19.0, npm 11.11.0, Python 3.11.5 and isolated PostgreSQL 17 binaries. The attached master plan was read as reference; only the user-supplied prompts 03–06 were implemented in this turn.

| Check | Result |
| --- | --- |
| PostgreSQL initial migration | Applied successfully to separate development/test databases |
| Migration round trip | Downgrade to base and re-upgrade passed on disposable data |
| Alembic schema drift check | No new operations detected |
| Backend integration/unit suite | **30 passed**, using real PostgreSQL for authentication and integrity tests |
| Authentication | Registration, duplicate registration, valid/invalid login, unauthorized/authorized access, admin/customer roles and logout/replay passed |
| Additional security checks | Expiry, disabled accounts, role injection, CSRF/origin/referrer checks, CORS, body limits, throttling and production cookie configuration passed |
| Database constraints | Decimal round trip, inventory limits, foreign keys, quantities, refund amounts, legal transitions and immutable histories/snapshots passed |
| Category seed | Run twice successfully; only three category rows, no duplicate or user seeds |
| Backend lint and dependency consistency | Ruff and pip check passed |
| Design-token contrast | All nine tested text/control pairs passed; smallest tested ratio 4.00:1 for input borders, exceeding its 3:1 target |
| Next.js production build | Passed with the Tailwind token stylesheet |
| Frontend lint and TypeScript | Both passed after adding the design-token checks |
| HTTP through Next.js | Placeholder, API health and PostgreSQL readiness returned 200; unauthorized identity returned 401; same-origin CSRF issuance worked |

The original phase-02 database limitation is resolved locally: PostgreSQL runs from ignored `.tools` paths on loopback port 55432, with separate `decor` and `decor_test` databases. The README documents starting/stopping it. This is not a system installation or production database.

Temporary frontend/backend processes and the isolated PostgreSQL instance were stopped after verification. Database files are retained; use the README commands to start them again.

CI now supplies PostgreSQL, executes the full suite, checks schema drift, exercises migration round trips and checks token contrast. GitHub CI itself has not run because no remote or push is configured. Local tests are not evidence of cloud deployment.

Two upstream test-client deprecation warnings remain (Starlette/httpx compatibility and an AnyIO portal alias). They are visible and do not fail the suite. ESLint 9 remains pinned for the previously verified Next.js lint-plugin compatibility issue.

No complete storefront/auth UI, payment integration, email verification/recovery, admin MFA, courier integration or production deployment has been implemented. No complete website is ready for customer review yet. Design-token checks do not replace rendered component accessibility testing when pages are built. Production launch still requires the security and operational gates in the architecture/authentication documents.

## Storefront redesign verification — 22 September 2026

- Frontend ESLint, TypeScript, production build and token contrast checks passed.
- All three frontend SEO tests passed. Three PostgreSQL demo seed tests passed, including idempotence, four distinct images per product, preservation of stock/image IDs and refusal to overwrite an unlabelled product. Existing upstream test-client deprecation warnings remain.
- Browser checks: desktop homepage/shop/product layout, Shop all, New arrivals (six items), The edit (three items), search for basket, four gallery views, keyboard arrows and zoom.
- Mobile 390px checks: homepage, product page and search listing; filters collapsed, no document overflow, no broken loaded product images.
- HTTP checks: homepage, three shop views, three categories, all six demo product pages, wishlist and cart returned 200. Database readiness returned ready.
- Generated source assets inspected: six four-view product sets plus hero, all portraits 1122 × 1402 and hero 1536 × 1024. All copied into the repository.
- Checkout/payment remain incomplete by phase design; no test payment or real order was placed.

## Cart and wishlist — 22 September 2026

- Backend: 94 PostgreSQL tests passed, including cart prices/discounts, quantity and ownership validation, guest/account merge, wishlist duplicates and archived products, and a populated migration upgrade/downgrade test.
- Alembic: database is at revision 0003; schema comparison reports no pending changes.
- Frontend: production Next.js build completed. Desktop and 390 px mobile cart/wishlist screens checked in the browser.
- Browser flows: save two demo products, wishlist-to-bag, quantity change and revised totals, PIN-code rejection without a delivery promise, reload persistence, sign-in merge for cart and wishlist, wishlist removal/empty state, sign-out and separate empty guest bag.
- Disposable local browser-test account was removed after signing out. No real customer accounts or orders were changed.
- Final frontend lint and TypeScript checks passed after the last changes. Local homepage, cart, wishlist and account routes returned HTTP 200; `/api/v1/ready` returned `ready`.

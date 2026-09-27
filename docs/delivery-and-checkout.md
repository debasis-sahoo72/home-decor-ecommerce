# Delivery and checkout — prompts 15–16

## Delivery policy

The `delivery_pincodes` table is the authoritative allowlist. A PIN must have both `active=true` and `urban=true`; unknown, inactive or unclassified/rural PINs are unavailable. City names never grant serviceability. Indian PIN input must be six ASCII digits, starting with 1–9.

Migration 0005 converts existing `next_day` entries to `standard`, with at least 3–5 days. The initial approved Bangalore PIN `560001` is enabled as urban standard delivery; other records default to unclassified (`urban=false`) until reviewed. Bangalore has the same standard-delivery policy as other enabled urban locations. Admin writes accept standard only and a minimum two-day window.

Assumption: estimates use calendar days, including weekends and holidays, in India time. At/after each PIN's cutoff an extra day is added. No holiday calendar or weekend exclusion was requested. Delivery estimates are recalculated from payment verification for confirmed orders using the snapshotted transit rule. A future shipping adapter belongs behind `app/services/delivery.py`, retaining the public quote shape.

An authenticated administrator can PUT `/api/v1/admin/delivery/{pincode}` with a session CSRF token and these fields:

```json
{"service":"standard","urban":true,"active":true,"min_days":3,"max_days":5,"cutoff_hour":12,"fee":"50.00"}
```

This example is a configuration shape, not verified coverage or a recommended shipping fee. Supply a carrier/business-verified urban PIN list before enabling real delivery. Public lookup remains GET `/api/v1/delivery/{pincode}`; cart and product checks use the same service.

## Customer flow

`/cart` and product Buy now lead to `/checkout`. Buy now adds the selected quantity to the bag, then reviews the whole bag. Guest carts merge at sign-in; checkout requires an active account. The checkout view supports saved address selection, the existing inline add/edit address book, delivery validation, server-calculated order review, secure payment and a private confirmation page. Mobile uses a single column. Demo product labels remain visible.

- POST `/checkout/quote`: own `address_id` only. Locks owner/cart/stock, validates product/category visibility and quantities, and calculates prices/discount/delivery from the database. Returns a quote hash.
- POST `/checkout/orders`: own `address_id`, UUID `idempotency_key`, and `quote_hash`. Extra fields, including client totals, are rejected. Recomputes the quote and requires re-review if changed. A user-row lock serializes concurrent submissions; a unique owner-scoped key replays the same order. Only one pending checkout per account is allowed.
- Inventory is reserved atomically with the awaiting-payment order. Address, delivery, items and prices are snapshotted. Carts themselves do not reserve inventory. PostgreSQL audit triggers record each state transition once, including actor/reason.
- POST `/checkout/orders/{id}/payment`: starts/resumes one Razorpay order with the exact server amount in paise. Initiation intent is committed before calling the provider. Ambiguous provider errors cannot blindly create another payment order.
- POST `/checkout/orders/{id}/confirm`: fetches the stored Razorpay order and its payments using server credentials. Requires paid order/captured payment and matching order ID, amount and INR currency. Frontend success data does not authorize payment. Repeated confirmations consume stock and clear purchased cart quantities only once.
- GET `/checkout/pending` resumes a checkout; GET `/checkout/orders/{id}` shows only the owner's order. Cancel before payment initiation via POST `.../cancel` releases stock. Private responses are `no-store`; mutations enforce session CSRF and same-origin policy.

Tax assumption: catalog prices are final tax-inclusive merchandise prices; no additional tax is calculated. Tax invoice/GST breakdown remains a later accounting requirement.

## Payment configuration and recovery

No new payment library is required; the backend uses a bounded-timeout HTTPS adapter and the browser loads Razorpay's hosted checkout only when paying. Credentials are server-only: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`. Only test keys are enabled outside production. Production requires live keys and a webhook secret. Missing configuration leaves payment disabled without creating orders or reserving stock. No simulated payment-success endpoint exists.

Configure Razorpay automatic capture and the signed `payment.captured` webhook at `/api/v1/payments/razorpay/webhook`. HMAC-SHA256 verifies the raw body; the backend then independently fetches captured payment details. The browser callback and webhook converge on the same idempotent confirmation service. A manual **Check payment status** action recovers an interrupted browser callback.

Unstarted checkouts expire after 30 minutes. On customer resume or reconciliation they are cancelled and stock is released. Run this from `backend` periodically (e.g. every five minutes via the deployment scheduler):

```powershell
.\.venv\Scripts\python.exe -m app.cli reconcile-checkout
```

Started payments deliberately retain their reservation until reconciled: a browser close or local timeout cannot prove that a charge failed. The command checks stored provider orders for captured payments. If provider creation timed out before the provider ID was saved, an operator must reconcile the receipt (local order number) against the Razorpay dashboard before repairing/releasing the hold. Automatic cancellation/refund of started payments and a provider reconciliation admin interface remain payment/operations follow-up work. This is a launch limitation, not a signal to release stock blindly.

External setup still required: verified urban coverage and shipping fees, Razorpay test credentials and dashboard capture configuration, a reachable webhook URL for provider testing, then live merchant configuration before launch. Tests use an injected provider fixture, never real charges.

## Verification

PostgreSQL integration tests cover standard Bangalore, other urban/rural/unknown PINs, invalid input, India-time cutoff/calendar dates, migration of old express records, admin validation, address/order ownership, CSRF, stock, stale quotes, tampered totals, idempotency, cancellation/expiry, provider timeouts, mismatched payments, authenticated webhook replay and successful settlement. Frontend checks include TypeScript, lint and production compilation.

Provider reference: [Razorpay standard integration](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/).

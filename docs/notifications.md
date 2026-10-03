# Transactional email and WhatsApp

Providers: Resend email API and Meta WhatsApp Cloud API, called through one `Providers.send` adapter. No new dependency, broker, Redis, scheduler or worker is required. Both channels are disabled by default; no live customer messages were sent during development.

## Events

- Registration: welcome email after the account commits. Registration does not collect WhatsApp consent, so no unsolicited WhatsApp welcome message is sent.
- Order confirmation and payment confirmation: separate transactional events after the backend verifies captured payment and commits the paid order. Pending/unpaid orders do not receive confirmation.
- Shipped/delivered: after the committed, authorized order status transition.
- Cancelled: after customer/admin cancellation or checkout-expiry reconciliation. Wording explicitly does not promise a refund.
- Refunded: `verified_refund_event` accepts only a stored full-refund payment. The future Razorpay refund workflow must call it in its verified transaction and dispatch after commit. The current application cannot perform refunds, so it cannot automatically trigger this event yet. Partial refunds are not represented as full-refund confirmations.

## Delivery and privacy

Each enabled event/channel gets a unique PostgreSQL delivery record inside the business transaction. Inline sending starts only after commit. Provider failures do not roll back the account/order. The record contains identifiers, event, status, attempt count, provider ID, safe error code and consent timestamp—not message bodies, email addresses or copied shipping information.

Email contains a brief event message and order reference. WhatsApp sends an approved template with one body parameter (the order reference). Neither channel sends names, passwords, session tokens, street addresses, item lists, totals or payment credentials. Logs contain delivery IDs and safe failure codes, never provider responses or recipient data. API keys stay in the ignored backend `.env`/production secret manager.

Customers manage WhatsApp at `/account/notifications`, linked from their account page. Consent is explicit, unselected by default, and tied to an E.164 number and timestamp. Delivery rechecks consent and account status. Opt-out clears the stored number; changed or renewed consent invalidates older pending WhatsApp deliveries. Shipping-recipient numbers are never automatically opted in. In-flight provider requests cannot be recalled after opt-out. Transactional email remains tied to the account email; this is not a marketing subscription system.

`accepted` means the provider accepted the request, not that the person received/read it. Delivery/bounce/read webhook reconciliation is not implemented. Resend requests use an idempotency key; a database unique constraint prevents normal event replays. A timeout/5xx or unexpected response becomes `unknown`. A process crash during sending leaves `sending`. Neither is automatically replayed because WhatsApp lacks the same idempotency guarantee. Inspect these in the provider dashboard before any manual reconciliation. Exactly-once external delivery is not promised.

Sending is inline with a five-second HTTP timeout per call; enabled payment confirmation can make four calls. This is suitable for initial low volume. If latency/volume becomes material, move the same `deliver` function to a supervised job runner. Pending receipts survive a crash between the business commit and dispatch. Notifications disabled at event time are not backfilled later.

## Configure email

Create a Resend account, verify a sending domain, configure its DNS records, and put these **backend-only** values in `.env`:

```dotenv
EMAIL_NOTIFICATIONS_ENABLED=true
RESEND_API_KEY=your_private_key
NOTIFICATION_FROM_EMAIL=Your Sanctuary <orders@your-verified-domain>
```

Restart the backend. First test with your own account/recipient allowed by your provider account. No credential needs to be committed to GitHub.

## Configure WhatsApp

Create/configure a Meta business WhatsApp Cloud API app and sender number. Obtain a messaging access token, phone-number ID, and a supported Graph API version from the dashboard. Get utility templates approved in the exact language configured below. Each template should contain its event-specific fixed wording and exactly **one body placeholder** for the order reference; avoid dynamic URLs/buttons/header placeholders with this initial adapter.

Example fixed template: `Your Sanctuary order {{1}} has been shipped. Sign in to your account for details.` Use separate fixed text for confirmed payment, confirmed order, delivery, cancellation (no refund promise), and verified refund. Approval is determined by Meta, not this application.

```dotenv
WHATSAPP_NOTIFICATIONS_ENABLED=true
WHATSAPP_ACCESS_TOKEN=your_private_token
WHATSAPP_PHONE_NUMBER_ID=your_numeric_phone_id
WHATSAPP_API_VERSION=vXX.0
WHATSAPP_TEMPLATE_LANGUAGE=en
WHATSAPP_TEMPLATES={"order_confirmed":"ys_order_confirmed","payment_confirmed":"ys_payment_confirmed","shipped":"ys_shipped","delivered":"ys_delivered","cancelled":"ys_cancelled","refunded":"ys_refunded"}
```

Replace `vXX.0` with a supported version (not a literal placeholder) and names with your approved templates. Enable only after configuration; restart the backend. Customers must opt in before future events can send WhatsApp updates. No provider costs/free-tier claims are assumed.

## Inspect/retry locally

Run from `backend` with the virtual environment Python:

```powershell
.\.venv\Scripts\python.exe -m app.notification_delivery
.\.venv\Scripts\python.exe -m app.notification_delivery --retry DELIVERY_UUID
```

Inspection prints the latest 50 safe delivery summaries. Retry sends only pending/definitely failed records, at most three attempts; accepted, unknown, sending, skipped and opted-out records are not resent. This is an operator command, not a public send endpoint. Old shipped messages may no longer be useful: inspect the current order/provider status before choosing a manual retry.

Migration 0009 adds the delivery log and WhatsApp preference fields. No automatic destructive retention is scheduled; include the new user phone preference in the production privacy/retention policy and restrict database/operator access.

Provider references: [Resend send API](https://resend.com/docs/api-reference/emails/send-email), [Resend idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys), [Meta Cloud API examples](https://github.com/fbsamples/whatsapp-api-examples), [Meta's published template request format](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/template/). The archived SDK is not installed; the adapter uses HTTP directly.

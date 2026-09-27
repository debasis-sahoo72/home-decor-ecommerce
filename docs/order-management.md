# Orders and initial store administration

Customer orders: `/account/orders`. Administrator dashboard: `/admin`.
Both use authenticated, no-store APIs. Every admin API checks the role on the
server; hiding a navigation link is not an authorization boundary. Mutations
also require CSRF validation. Customer order queries always scope by the session
owner and return 404 for another customer's order ID.

## Local setup

From the backend directory run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli create-admin
```

The second command prompts for a new administrator email and passphrase; it
never promotes an existing customer. Sign in at `/login?next=admin`. No default
admin password is shipped. Restart the backend if it is not running with reload.

## Creating and tracking orders

Checkout reviews the authenticated customer's address, serviceable PIN, stock,
and server-calculated totals. `POST /api/v1/orders` accepts the address ID,
quote hash, and idempotency key, never client totals. It can save a pending order
without payment credentials. Retrying the same key returns the same order;
one pending checkout per customer prevents duplicate stock reservations.

The checkout button **Save order awaiting payment** opens the order detail page.
This does not charge a card or confirm a purchase. Unstarted reservations expire
after 30 minutes and are released on checkout reconciliation or the customer's
next pending-checkout lookup. Run the existing `reconcile-checkout` CLI regularly
before production; no background scheduler was added in this phase. Started
payments retain their reservation until reconciled.

## Status rules

API/UI statuses map to existing storage: PENDING_PAYMENT = `awaiting_payment`,
CONFIRMED = `paid`; the other requested names use their lowercase spelling.
Migration 0006 preserves existing orders and immutable snapshots.

```text
PENDING_PAYMENT → CONFIRMED → PROCESSING → PACKED → SHIPPED
    → OUT_FOR_DELIVERY → DELIVERED → RETURN_REQUESTED → RETURNED

PENDING_PAYMENT / CONFIRMED / PROCESSING / PACKED → CANCELLED
RETURN_REQUESTED → DELIVERED (return request rejected; reason required)
CANCELLED / RETURNED → REFUNDED (reserved for verified refund integration)
```

The first line is one continuous fulfilment chain. Admin changes require the
expected current status and a reason. Concurrent stale updates fail with 409.
Both application validation and PostgreSQL triggers reject invalid transitions;
the append-only audit records actor, reason and chronological timestamps.
Customers see the status timeline without internal staff notes.

Admins cannot manually confirm payment or assert a refund. CONFIRMED requires
the existing trusted payment verification path; REFUNDED is defined in the state
graph but its API action remains blocked until verified refund handling is
implemented in the upcoming Razorpay phase. No new payment integration is enabled.

Cancelling an unstarted pending checkout releases reserved stock. Cancelling a
confirmed pre-dispatch checkout restores the consumed stock once. A started,
unverified payment must be reconciled before cancellation. Cancellation does not
mean a refund has happened. Legacy orders without checkout reservation metadata
are not automatically restocked. Returned goods require inspection and a manual
inventory adjustment; they are not automatically made sellable.

## Admin operations

- Dashboard: orders created today (all statuses); gross payment captures today;
  pending payment/confirmed/processing/packed orders; distinct active products
  with an active variant having five or fewer available units. Day boundaries
  use Asia/Kolkata. Revenue is gross captures, not profit or net of refunds.
- Products: search, create/edit descriptions, category, SEO, active/featured
  status, specifications, SKUs and prices, and manage validated Cloudinary uploads
  through the [product media editor](cloudinary-media.md).
  New product forms default to inactive. Add variants and inventory before
  activating. Existing catalog API validation applies to every write.
- Categories: create/edit names, slugs, descriptions and SEO/active status.
- Inventory: search SKUs, filter low stock, adjust on-hand quantities. Reserved
  units remain protected by the existing inventory service and DB constraints.
- Orders: paginate, search order number/customer name/email, filter status/date,
  inspect frozen address/items/totals and payment records, update fulfilment.
- Customers: read-only operational list; password hashes and sessions are absent.
- Delivery PIN codes: explicitly add/edit urban standard-delivery coverage.
  Database migrations do not guess coverage or add serviceable PINs; locally
  configured coverage remains unchanged. No rural/express promises are made.
- Reviews: inspect genuine stored reviews and publish/reject/return to pending.
  No reviews or paid orders are invented to populate the dashboard.

## Verification

`tests/test_operations.py` covers all 121 state pairs, authenticated ownership,
idempotent pending-order creation without payment setup, complete fulfilment,
database transition rejection, audit history, stale updates, cancellation stock
integrity, payment guards, filters, metrics, moderation and admin authorization.
The existing checkout/catalog/address/auth suites continue to cover those APIs.

# Customer addresses — phase 14

Customer address book: `/account/addresses`, linked from the signed-in account screen. The page uses the shared cream/forest-green design and supports add, edit, delete confirmation and setting a default address. Authentication is required; signing in from the address page returns there.

## Data and validation

- API fields: `full_name`, `phone`, `line1`, optional `line2`, optional `landmark`, `city`, `state`, `country`, `pincode`, optional `is_default`.
- `full_name` maps to the existing `addresses.recipient` column, preserving compatibility. Migration 0004 adds landmark, country and default status; existing rows retain their data, with the oldest address per user chosen as default.
- Assumption: this store currently accepts India (`IN`) addresses and Indian mobile numbers only. Phone input accepts 10 digits or a +91 prefix and stores normalized +91 format. PIN codes must contain six digits and start 1–9. City/state text supports Unicode; no external geocoding dependency is introduced. Length bounds, whitespace trimming and control-character rejection apply. Optional blank fields become null. Unknown fields, including a caller-supplied `user_id`, are rejected.
- Saving an address does not confirm delivery serviceability. Checkout must check the configured delivery rules independently.
- Up to 20 addresses per customer. First address becomes default automatically. Editing the default does not unset it; choose another default instead. Deleting it promotes the oldest remaining address. There are zero defaults only when the address book is empty.

## API and ownership

All routes are under `/api/v1/addresses`:

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/addresses` | List only the current user's addresses, default first |
| GET | `/addresses/{id}` | Read an owned address |
| POST | `/addresses` | Create an address for the authenticated user |
| PUT | `/addresses/{id}` | Replace the editable fields of an owned address |
| POST | `/addresses/{id}/default` | Set an owned address as default |
| DELETE | `/addresses/{id}` | Delete an owned address |

Every lookup includes both address ID and authenticated user ID. Another user's UUID returns the same 404 as a missing record; admins do not bypass ownership. Anonymous requests return 401. Writes require session CSRF and allowed origin. Responses, including errors, are marked `Cache-Control: no-store`; address contents are not written to request logs or browser storage.

Mutations lock the owner row to serialize same-user changes; PostgreSQL additionally enforces at most one default per user with a partial unique index. Addresses are not soft-deleted: they are editable customer data, while future orders retain their own immutable delivery-address snapshots.

## Verification

Tests cover create/read/edit/delete, first/default promotion, phone normalization, validation, forged ownership fields, cross-customer isolation for all ID operations, CSRF, login, limits, and migration preservation/default backfill. Existing cart, wishlist, auth and catalog tests remain in the suite.

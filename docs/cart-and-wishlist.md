# Cart and wishlist (phases 12–13)

The shared ivory, forest-green and warm-brown design follows `storefront-reference.png`. Cart thumbnails retain the 4:5 product image contract. Demo records remain explicitly labelled.

## Cart contract

- `GET /api/v1/cart` returns owned items and current server-calculated INR totals; optional `?pincode=560001` checks actual configured delivery rules.
- `POST /api/v1/cart/items` accepts only `variant_id` and integer `quantity` (1–100).
- `PATCH /api/v1/cart/items/{id}` replaces quantity; `DELETE` removes an owned line. `DELETE /api/v1/cart` clears the owned cart.
- PostgreSQL persists guest carts behind a signed, expiring HTTP-only cookie (30 days) and account carts by authenticated user ID. Guest cookies cannot select an account cart. Expired sessions return 401 rather than falling back to guest ownership.
- Sign-in merges a guest bag into the account bag, combines matching variants and caps quantities to available stock. Unavailable items remain visible for removal. A combined bag above 100 distinct options is rejected for review. Sign-out leaves the account cart intact and starts a separate guest bag.
- Writes lock the owning cart and validate active catalog records and unreserved inventory. Adding does not reserve inventory. Future order creation must atomically recheck prices and reserve stock.
- Totals use Decimal database prices. `subtotal` is compare-at value (or regular price); `discount` is product savings; `merchandise_total` is selling price total. `delivery_fee` and `total` are null until a serviceable PIN and valid stock are present. No coupon, tax or free-shipping rules are fabricated. A quote is an estimate, not a placed order.
- Prices, quantities and stock are refreshed after each cart change. All personal cart/wishlist responses are `no-store`. Mutations require origin and CSRF validation. Client mutations serialize CSRF-token refreshes within a tab.

## Wishlist contract

- Guest wishlist product IDs remain in local device storage; clearing browser storage removes them. Device storage holds at most 200 IDs.
- Signed-in `GET /api/v1/wishlist`, `POST /api/v1/wishlist/items`, and `DELETE /api/v1/wishlist/items/{product_id}` use PostgreSQL account ownership. `POST /api/v1/wishlist/merge` imports device IDs at sign-in, skips unavailable products, and clears the device list only after success.
- Product uniqueness is enforced by a database constraint and parent-row locking. Products with multiple variants link to option selection before adding; single-variant cards add directly using server stock validation.
- Inactive/archived products are excluded from product cards; existing unavailable saved IDs can still be removed.
- Migration `0003` converts the unused variant-based wishlist schema to product-based entries and deduplicates variants of the same product. Downgrade selects one variant per product and cannot represent products without variants; back up before any production downgrade.

## Local verification

Run `scripts/start-local.ps1` from the repository root to apply migrations and start/check the local services. Open `/cart`, `/wishlist`, or `/login` at `http://127.0.0.1:3000`. Existing labelled demo products can be used immediately. There are deliberately no seeded delivery promises: configure actual serviceability data to see a positive delivery quote.

Backend integration tests require a disposable PostgreSQL database ending in `_test`; set `TEST_DATABASE_URL` then run `.venv\Scripts\python.exe -m pytest -q` from `backend`. Tests cover quantity validation, price tampering, current prices/discounts, delivery quotes, account/guest isolation, sign-in merge and stock cap, session persistence, CSRF, wishlist duplicates and unavailable products. Frontend validation uses lint, TypeScript/production build and desktop/mobile browser checks.

Checkout/payment are still later phases; the cart explicitly displays a disabled checkout control. This release includes basic registration/sign-in/sign-out so account cart and wishlist handling can be used. It is not a full account/orders dashboard.

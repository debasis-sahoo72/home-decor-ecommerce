# Prompt 11 — Product detail

The canonical route is `/product/[slug]`. Existing `/products/[slug]` links redirect
permanently. Metadata, Open Graph imagery and escaped Product JSON-LD are rendered
on the server. Offers use actual variant prices and stock; aggregate ratings appear
only when published reviews exist. No shipping claim appears in structured data.
Reference: https://developers.google.com/search/docs/appearance/structured-data/product-snippet

The page includes a keyboard-accessible image gallery with meaningful alt text,
variant selection, SKU, stock, discounts, bounded quantity, description,
specifications, wishlist, published reviews with pagination, and related products.
Related products use the active category catalog, excluding the current product.
Empty reviews and missing photography are explicitly identified.

## Purchase actions and scope

Add to bag calls `POST /api/v1/cart/items` with a variant UUID and integer quantity.
The server serializes cart updates, checks current product/category/variant status
and locks inventory while validating the accumulated quantity against on-hand minus
reserved. It accepts no client price. Stock is not reserved by adding to a cart.
`GET /api/v1/cart` returns current prices and availability; item removal is scoped to
the cart token via `DELETE /api/v1/cart/items/{id}`. The `/cart` page supports viewing
and removing items.

Cart ownership is browser-specific in this phase, using a signed, expiring,
HTTP-only, SameSite cookie (Secure and __Host-prefixed in production). Only its hash
is stored in PostgreSQL. Tokens expire after 30 days. Signed-in mutations use session
CSRF protection; guest mutations use the existing pre-auth CSRF mechanism. Cross-device
account cart merging and abandoned-cart cleanup belong to the later cart phase.
Never assume possession of a user account merges an existing browser cart.

Buy now calls `POST /api/v1/checkout/preview` and routes to `/checkout` after stock
and serviceability pass. The purchase review checks again on arrival and clearly
states that payment is unavailable. **No order is placed, no stock is reserved and
no payment is taken.** Full checkout, totals/taxes, reservations and Razorpay remain
later phases. Order creation must recheck prices, serviceability and available stock
and reserve inventory transactionally before accepting payment; this preview is not
an authorization to place an order.

## Delivery and reviews

`GET /api/v1/delivery/{pincode}` accepts exactly six ASCII digits and returns no
estimate for missing or inactive rules. Active `delivery_pincodes` provide min/max
calendar days, shipping fee and a cutoff hour interpreted in India time (UTC+05:30).
At or after the cutoff an extra day is added. These are estimates, never guarantees.
Configure only genuinely serviceable PIN codes. Weekend/holiday calendars and carrier
SLAs require the later delivery phase. No production delivery rules are seeded.

`GET /api/v1/products/{uuid}/reviews?page=1` returns ten published reviews per page,
ordered stably by timestamp and ID. It exposes the reviewer's first name, not email,
and applies public product visibility rules. It makes no verified-purchase claim.

## Verification

- Backend tests cover guest and signed-in CSRF, cart isolation, token forgery/expiry,
  negative/fractional/excess quantities, accumulated stock, unavailable products,
  missing/inactive PIN codes, India-time cutoff, purchase revalidation, and review privacy.
- `npm test` covers JSON-LD injection escaping, canonical offers and genuine ratings.
- Run backend pytest/Ruff/Alembic checks and frontend lint/typecheck/build/contrast checks
  using the commands in the README. No new runtime dependency or table is required.
- Real inventory, Cloudinary photography and approved delivery rules are required to
  populate a production product page. Browser QA fixtures are temporary and removed.

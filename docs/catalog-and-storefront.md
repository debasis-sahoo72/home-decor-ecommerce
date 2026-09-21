# Phases 07–10: catalog and storefront

Project location: `C:\Users\sonal\Projects\home-decor-ecommerce`.

## Catalog model

A category contains products. A product describes a design; variants hold its SKU,
price and inventory. Even a simple product has one `Standard` variant. Images are
ordered Cloudinary references, never binary database content. Categories and
products have active flags, descriptions and SEO metadata. Product specifications
are a bounded JSON object of text values. Products without active variants do not
appear publicly. Inactive/archived products or categories are hidden from public
detail, search and listing APIs. Out-of-stock products remain discoverable.

Money travels as decimal strings in INR. Discounts use the variant's compare-at
price, rounded to the nearest whole percentage. Stock availability is on-hand
minus reserved; an admin cannot reduce on-hand below reserved. Stock updates lock
the inventory row until commit. Database constraints remain the final safeguard.
Variant IDs are retained when editing, preserving cart/order references. Deactivate
products and variants instead of deleting them.

## Public endpoints under `/api/v1`

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/categories` | Active categories |
| GET | `/categories/{slug}` | Category detail |
| GET | `/products` | Search/filter/sort/paginated catalog |
| GET | `/products/{uuid}` | Product detail |
| GET | `/products/slug/{slug}` | Product by SEO slug |

Products accept `q`, `category` (slug), `min_price`, `max_price`, `in_stock`,
`featured`, `sort`, `page`, `page_size`. Sorts: `newest`, `price_asc`, `price_desc`,
`name`, `best_sellers`. Page size defaults to 12 and is capped at 48.
Price sorting uses the lowest active variant price. Price filtering and stock
filtering must match the same variant. Cards show the lowest active variant's
price and discount, which can differ from the variant matching a price filter.
Search uses PostgreSQL English full-text search and a GIN index. It supports whole
words and stemming, not typo tolerance or arbitrary substring matching.
Stable ID tie breakers prevent unstable ordering of equally priced products.

Best sellers count quantities on paid, processing, shipped or delivered orders.
They are hidden when there is no qualifying sales history. Ratings come only from
published review records; pending reviews and invented testimonials are excluded.
Refund-aware popularity ranking can be added alongside the refund implementation.

## Admin workflow

Admin writes require a logged-in active admin, an allowed `Origin` header, the
session cookie and `X-CSRF-Token`. Use the existing admin provisioning command
documented in the README; public registration never grants admin access.
Use `/auth/csrf` and `/auth/login` as documented by OpenAPI at `/docs`.

1. `POST /admin/categories` with name, lowercase hyphenated slug and optional metadata.
2. `POST /admin/products` with `category_id`, name, slug, description, specifications,
   optional SEO metadata and `featured`. Initially set `active: false` while editing.
3. `POST /admin/products/{id}/variants` with SKU, label, price and optional compare-at price.
4. `PUT /admin/variants/{id}/stock` with `{"on_hand": 10}`.
5. `POST /admin/products/{id}/images` with Cloudinary public ID, HTTPS upload URL,
   descriptive alt, position, width and height.
6. `PUT /admin/products/{id}` with the complete product fields and `active: true`.

PUT replaces editable fields with the submitted values/defaults; it is not PATCH.
Other editing endpoints: `PUT /admin/categories/{id}`, `PUT /admin/variants/{id}`,
`PUT /admin/images/{id}`, `DELETE /admin/images/{id}`. Image deletion removes only
the database reference, not the Cloudinary asset. Image positions/public IDs are
unique; move to a vacant position before swapping positions.
Admin reads: `GET /admin/categories`, `GET /admin/products?page=1` (24 per page).
Duplicate slug, SKU or image conflicts return 409; invalid input returns 422.
The existing 16 KiB request-body limit applies to each write.

## Frontend

Routes: `/`, `/shop`, `/categories/{slug}`, `/product/{slug}`, `/wishlist`.
Prompt 11 adds the full product page and redirects legacy `/products/{slug}` URLs.
See [product detail](product-detail.md) for bag, delivery and purchase-review behavior.
Server-rendered pages use a typed server API client with an eight-second timeout
and no persistent catalog cache, so admin edits become visible on the next page
request. The existing same-origin `/api` rewrite supports browser requests.
Native GET filter forms work without JavaScript, preserve filters in shareable
URLs, and reset pagination when applying new filters. Mobile filters use a native
collapsible details element. The header, footer, product grid and cards are shared.
Only error recovery and saved-piece interactions require client components.

Saved pieces are local to the browser/device, limited to 200 IDs. Storage failure
is announced; unavailable products are omitted when viewing the saved list.
Account synchronization belongs to phase 11. Product detail is deliberately a
read-only destination in phases 07–10; prompt 11 extends it with validated bag and purchase-review actions.

The homepage shows real API categories and new arrivals, an editorial feature and
qualifying best sellers. No fake reviews, Instagram feed or nonfunctional newsletter
form is shown. There is no unconditional next-day delivery claim.
The two Unsplash interior photographs are editorial inspiration, not catalog
inventory: `photo-1600210492486-724fe5c67fb0` and
`photo-1600607687920-4e2a09cf159d`. Replace with approved brand photography before
launch. Product images use Cloudinary; Next Image handles responsive optimization.
Missing product photography has an explicit placeholder and stable dimensions.

## Environment and verification

Frontend: `BACKEND_URL` is server-only; `SITE_URL` supplies absolute metadata URLs.
Set `SITE_INDEXABLE=true` only on the public production site. Filter/search pages
remain noindex and canonicalize to the unfiltered collection. Saved pieces are
always noindex. The default local site is noindex.

After updating code, from `backend` run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
$env:TEST_DATABASE_URL='postgresql+psycopg://decor:local-development-only@127.0.0.1:55432/decor_test'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m alembic check
```

From `frontend`, run `npm run lint`, `npm run typecheck`, `npm run check:contrast`
and `npm run build`. Standard startup commands remain in the README.
The catalog migration is `0002_catalog.py`. Tests use isolated transactions on a
disposable PostgreSQL database whose name must end in `_test`.

No sale products or users are automatically seeded. Add actual inventory through
the admin API before expecting product grids or best sellers on the homepage.

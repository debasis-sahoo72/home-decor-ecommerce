# Performance audit — 30 September 2026

## Result and measurement limits

Two measured N+1 query paths were fixed without changing prices, stock rules, authorization, response contracts or adding infrastructure. Public catalog reads were already batched. No Redis or other cache service is justified by this evidence.

This is a source review across storefront, account/admin, catalog, cart/wishlist, checkout/orders, delivery, media, notifications, SEO and connection management, with targeted local profiling. It is **not** a production load certification. No real customer data was generated or changed. SQL measurements use synthetic data in the disposable PostgreSQL test database, rolled back afterwards. Provider latency, production CDN behavior, mobile rendering, Core Web Vitals and concurrent traffic remain unmeasured.

## Reproducible database measurements

`backend/tests/test_performance.py` creates 1 or 24 distinct products, one variant per product, one shared category and a cart. Before each read it clears the SQLAlchemy identity map so cached ORM objects cannot hide lazy loads. It counts SELECTs using SQLAlchemy events and prints elapsed service time and serialized JSON size. These are service calls, excluding HTTP, authentication and network overhead. There are no images or reviews in these synthetic records.

| Read path | Products | SELECTs before | SELECTs after | Observed before → after ms | JSON bytes after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cart | 1 | 7 | 7 | 37.96 → 24.49 | 604 |
| Cart | 24 | 99 | 7 | 108.59 → 8.42 | 9,619 |
| Public catalog | 1 | 7 | 7 | 39.64 → 18.72 | 813 |
| Public catalog | 24 | 7 | 7 | 22.21 → 10.20 | 18,106 |
| Admin `/admin/products` | 1 | 5 | 5 | 7.36 → 5.51 | 715 |
| Admin `/admin/products` | 24 | 74 | 5 | 76.60 → 7.05 | 17,202 |

Timings are single diagnostic runs, affected by warm-up and machine load; the unchanged public path also got faster. **The verified improvement is query count**, not a claimed production speed-up. Before/after response sizes were identical. Regression assertions cap these reads at 7/7/5 SELECTs respectively at both fixture sizes.

Changes: cart reads batch variants, stock, products, categories and images; the legacy admin product list now eager-loads its serialization relationships. The separate `/admin/catalog` implementation already uses eager loading (see the router prefix in `api/operations.py`). No write/locking path was weakened.

Run from `backend`, after setting `TEST_DATABASE_URL` to your disposable PostgreSQL database ending in `_test`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_performance.py -q -s
```

Verification: **330 backend tests passed**, including the new query-growth checks; targeted Ruff checks passed. Two existing third-party deprecation warnings remain.

## Frontend measurements

Read-only requests against the already-running **development** server at `127.0.0.1:3000`; five warm requests per route, full response elapsed time, not TTFB or LCP:

| Route | Warm samples, ms | Median ms | Decoded HTML bytes |
| --- | --- | ---: | ---: |
| `/` | 364, 279, 224, 222, 251 | 251 | 82,520 |
| `/shop` | 154, 199, 205, 173, 153 | 173 | 62,136 |
| `/shop?on_sale=true` | 136, 155, 133, 161, 130 | 136 | 47,893 |

Initial homepage/shop requests took about 3 seconds including possible development compilation. These are not production regressions. Each sampled page referenced 16 initial script URLs: approximately 3.87 MB decoded / 850–851 KB locally gzip-compressed, **including development tooling**. This is not browser transfer size or production bundle size; do not set a launch budget from it.

Hero source: 2,355,518 bytes. The existing Next image endpoint with WebP Accept, width 1080 and quality 75 returned **81,564 bytes**, HTTP 200, in 15 ms on the observed request (cache state unknown): about **96.5% fewer bytes** than the source. Its development cache header was `public, max-age=0, must-revalidate`; check deployed behavior separately. Source PNGs up to ~3 MB are not automatically downloaded at that size when rendered through `next/image`.

## Frontend findings and recommendations

| Area | Evidence/current behavior | Recommendation and measurable acceptance |
| --- | --- | --- |
| Server rendering | Homepage, shop/category and product route content are server components; interactive controls are client components. Root provider receiving children does not itself convert server-rendered children into client modules. | Preserve these boundaries. Profile production bundles before moving additional components. |
| Homepage dependency | Hero markup awaits all three catalog requests, although they already run in parallel with `Promise.allSettled`. Each fetch permits 8 seconds. | Separate independent catalog sections behind Suspense so a delayed offers API does not hold back hero rendering. Verify with an injected 2-second offers delay: hero response should not incur that delay. Preserve error/empty UI and category image behavior. |
| Product dependency | Detail is followed by parallel reviews and related products; rendering waits for both. | Stream these lower-page sections independently. Verify product name/main image render while related products are delayed. |
| Loading UI | Root `loading.tsx`, local busy/empty/error states exist. | Add scoped skeletons when splitting async sections, with final image/card dimensions to avoid layout shifts. |
| Images | `next/image`, responsive `sizes`, fixed containers, lazy non-hero images and preloaded hero/gallery exist. | Keep originals for editing; verify mobile candidate widths and cache hits in a production browser. Target hero transfer under 150 KB at the chosen mobile width, subject to visual quality. Do not preload every product image. Use versioned assets when replacing photos. |
| JavaScript | `shell.tsx` is client-marked and includes the static footer; account/admin components are interactive; Razorpay script is loaded on demand. | Separate footer into a server component only if bundle analysis shows worthwhile savings. Measure production route JS before/after; target no increase in initial storefront JS and no payment SDK request before checkout needs it. |
| Wishlist requests | Provider loads `/auth/me`, then full account wishlist but retains IDs; `saved-products.tsx` fetches every saved product individually in batches of six (up to 200). | Highest-priority frontend follow-up: reuse account wishlist items, and offer a bounded bulk public lookup for guest IDs. Target one paginated account request instead of N product requests; verify unavailable products and login merges still work. |
| Header counts | Header reads a full cart on mount/focus and any `shopping:changed`, including wishlist changes. Other screens also read identity/cart. | Separate cart/wishlist invalidation events, share request results or a minimal authorized count endpoint; coalesce overlapping refreshes. Target zero cart requests for wishlist-only toggles and one identity read per mount. Never cache counts across users. |
| Request caching | React `cache` deduplicates identical server calls within a render; underlying catalog fetch is `no-store`. | Retain fresh stock/prices and all private responses. Consider a short public category cache only with explicit invalidation on admin edits and measured hit rate; no global caching of auth/cart/checkout. |
| SEO/sitemap | Sitemap walks all catalog pages sequentially, loading full descriptions/images/variants. | At larger catalog size, add a slim sitemap projection and split/cached sitemap with explicit publication invalidation. Compare bytes and duration at 1k/10k products; avoid one full catalog scan per crawler request. |

## Backend findings and recommendations

| Area | Evidence/current behavior | Recommendation and measurable acceptance |
| --- | --- | --- |
| Index coverage | Unique slug/SKU/PIN keys; FK indexes; partial public-created and active-price indexes; GIN full-text search; owner/date and status/date order indexes exist. | No speculative index migration. Use `EXPLAIN (ANALYZE, BUFFERS)` on representative search, offers, newest and order queries at 1k/10k products and realistic order counts. Match plans to actual sort/filter selectivity. |
| Catalog queries | Public list uses batched relationships and one rating aggregate; 7 SELECTs in both measurements. Price and best-seller sorts use correlated subqueries; best-seller aggregates order items per product. | Keep existing correctness. Profile best-sellers on large order history before considering a grouped aggregate query. Require lower measured execution time/buffers with identical result ordering. |
| Remaining N+1 | Admin reviews serialize `db.get(Product, r.product_id).name` per review. Source-confirmed risk, not benchmarked here. Order lists already eager-load items; wishlist products are batched. | Batch review product names or join a projected name. Add a distinct-product review fixture and require constant SELECT count from 1 to 24 reviews. |
| Pagination | Catalog max 48/page; operational lists 24; reviews 10. Offset pagination permits deep pages. Category lists are unpaginated; wishlist is capped at 200, cart at 100 distinct options. | Retain small-store behavior. At deep-page p95 above 300 ms, compare cursor pagination for operational lists. Keep SEO public URLs stable. Watch category growth rather than introducing pagination prematurely. |
| Response sizes | Catalog uses full detail representation, including all images, descriptions, specs and variants. Minimal fixture was 18.1 KB/24, not a realistic upper bound. | Add list-specific projection if rich-catalog payload exceeds 100 KB decoded per 24 cards. Keep full detail endpoint. Check clients/admin/SEO before altering contracts. Measure bytes with four photos and realistic descriptions/variants. |
| Checkout | Validates and locks each variant in stable order, then calculates server prices; correctness matters more than reducing statement count. External payment operations can dominate. | Profile 1/10/100-line checkout separately. Any bulk-lock rewrite needs concurrency and stock-integrity tests; do not simply remove locks or cache quotes. Track p95 transaction/lock duration. |
| Connections | App engine uses pool size 5 + overflow 5, pre-ping, 3s connect timeout, request session cleanup and engine disposal. CLI module defines a separate engine. | Budget up to 10 connections per active application process plus CLI/maintenance clients, below PostgreSQL capacity. Measure checkout wait under 1/5/10 concurrent users before raising pool size. Configure bounded pool/query/lock timeouts after testing error handling. |
| Notifications | Dispatch is synchronous after commits, with external HTTP calls using 5s timeout. Multiple sends can extend request time. | Record provider duration separately from DB duration. If this dominates p95, use existing persisted notification records with a simple background dispatcher/CLI worker and retries. No Redis requirement. Preserve durable delivery and idempotency. |
| Media | Validation/Cloudinary uploads are offloaded to a threadpool; remote call timeout 30s, body limited to 5 MB. | Load-test concurrent uploads separately from storefront traffic; track worker saturation/memory. Keep validation and upload limit. Reuse an HTTP client only after measuring connection setup cost. |
| Delivery | Exact PIN lookup uses the indexed/unique PIN field; no city scans. | No cache needed based on current evidence. Maintain fresh serviceability at checkout. |
| Compression | Local decoded measurements do not demonstrate deployed compression. | Verify CDN/proxy Brotli or gzip for public HTML/JS/CSS; avoid indiscriminate compression/caching of sensitive authenticated responses. Record transferred and decoded sizes separately. |

## Production verification plan and budgets

1. Use an isolated staging database with realistic synthetic catalog sizes, never the live customer database. Run an optimized `npm run build` / `npm run start` frontend, not development mode, with the same deployment region as the backend/database.
2. Capture homepage, category, product, offers, guest/account cart and checkout on mobile and desktop; three cold and five warm runs, fixed network/CPU settings, browser/version recorded. Save waterfall, route JS, image candidate sizes and long tasks. Compare medians and tail values separately.
3. Proposed initial application budgets: warm public API p95 <=300 ms, server-rendered page TTFB <=800 ms, error rate <1% during a 10-minute 10-user synthetic browse/cart workload. These are **targets, not results or capacity promises**. Exclude intentional validation errors and measure provider time independently.
4. Core Web Vitals launch goals at the 75th percentile, segmented mobile/desktop: LCP <=2.5s, INP <=200ms, CLS <=0.1. Field data must confirm these after launch; a local HTTP fetch cannot measure them. See [Google's Web Vitals guidance](https://web.dev/articles/vitals).
5. For slow SQL, save SQL without customer parameters, plan, row counts, buffers and execution time. `EXPLAIN ANALYZE` executes the statement: use representative read-only queries in staging and account for profiling overhead. See [PostgreSQL EXPLAIN guidance](https://www.postgresql.org/docs/current/using-explain.html).
6. Change one bottleneck at a time, rerun identical workload, and keep functional/ownership/payment tests green. Do not trade inventory/payment correctness for latency. No production browser/load-test results are claimed in this audit.

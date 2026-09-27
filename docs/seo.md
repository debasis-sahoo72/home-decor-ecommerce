# SEO implementation and route review

The site uses server-rendered Next.js metadata and safely serialized JSON-LD. Copy uses product/category names, descriptions and optional admin SEO fields; no generated keyword lists, reviews, delivery promises or unsupported policies.

| Route | Search treatment |
| --- | --- |
| `/` | Natural title/description, self canonical, branded Open Graph and Twitter image |
| `/shop` | Collection title/description, self canonical, sharing metadata |
| `/categories/[slug]` | API-derived title/description with natural fallback, self canonical, breadcrumb JSON-LD; empty categories noindex |
| `/product/[slug]` | API-derived metadata, product photo sharing, canonical, Product and Breadcrumb JSON-LD; real price/stock and published-review aggregates only |
| Product review pagination | Noindex, canonical to the product |
| Shop/category pagination | Page-specific title and self canonical; out-of-range pages use not-found |
| Search, filters, sorting and other listing query strings | Noindex/follow; canonical drops filters and preserves valid pagination |
| `[DEMO]` products | Always noindex; omitted from sitemap and Product rich-result markup |
| `/products/[slug]` | Permanent 308 redirect to `/product/[slug]` |
| `/login`, `/cart`, `/wishlist`, `/checkout` | Noindex/nofollow metadata and HTTP X-Robots-Tag |
| `/account/**`, `/admin/**` | Inherited noindex/nofollow metadata and HTTP header; API authorization remains enforced |
| `/api/**` | Noindex header and production robots disallow |
| Unknown or inactive products/categories and unknown routes | Next not-found boundary with noindex; nonstreamed responses return 404. Already-streamed responses may retain 200 with the noindex boundary |

Semantic structure retains one main landmark, descriptive headings, linked product/category navigation, accessible controls, and breadcrumb navigation. Product images use stored alt text with product-name fallback. Decorative backgrounds and repeated hover/thumbnail images intentionally have empty alt text.

## Sitemap and robots

`/sitemap.xml` reads all public catalog pages (48 products/request), removes demos and duplicates, and includes only populated real-product categories. Private, query and legacy URLs are excluded. API failure fails the sitemap instead of publishing a partial success. No artificial last-modified dates are emitted. Split sitemaps are required before approximately 45,000 catalog products; a guard prevents silently exceeding the XML limit. For a large catalog, replace repeated full-product reads with a lightweight paginated SEO feed.

On an indexable deployment, robots permits public crawling and blocks API paths. Private HTML is crawlable so search engines can read its noindex directives; robots is not authorization. Local/staging sites disallow all crawling, emit noindex HTTP headers and return an empty sitemap.

## Production setup

Keep `SITE_INDEXABLE=false` locally and on previews. At launch set `SITE_URL` to the real HTTPS origin (no path/query/credentials) and `SITE_INDEXABLE=true` **before building**, then rebuild/restart. Localhost and non-HTTPS indexing settings are rejected. Use the same values at build and runtime. Configure the host to redirect HTTP and alternate hostnames to that canonical origin; no production domain has been provided yet.

Remove/deactivate demo products before launch. Keep published slugs stable. If an established slug must change, add an explicit old-to-new permanent redirect in `next.config.ts` before changing it; arbitrary former slugs are not automatically remembered. Do not redirect deleted products to an unrelated product or the homepage.

After public deployment, submit the sitemap in Google Search Console and validate representative real products with the Rich Results Test and URL Inspection. These external launch checks cannot validate localhost and have not been completed. Structured data does not guarantee rich results.

## Verification

Run `npm test`, `npm run typecheck`, `npm run lint`, and `npm run build` in frontend. With the local servers running and indexing disabled, run `node scripts/check-seo.mjs` for rendered route/header checks. Unit tests cover canonical pagination, query noindex, domain validation, structured data, sitemap paging/filtering/failure, and private headers on indexable deployments.

References: [Google pagination guidance](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading), [Product structured data](https://developers.google.com/search/docs/appearance/structured-data/product-snippet), and the installed Next.js metadata/robots/sitemap/redirect documentation.

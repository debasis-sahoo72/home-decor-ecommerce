import test from "node:test";
import assert from "node:assert/strict";
import { breadcrumbJsonLd, listingSeo, publicMetadata, siteSettings } from "../src/lib/seo.ts";
import { catalogPaths } from "../src/lib/sitemap-catalog.ts";
import type { Category, Product, ProductPage } from "../src/lib/catalog.ts";
import nextConfig from "../next.config.ts";

test("indexing is opt-in and requires an unambiguous public HTTPS origin", () => {
  assert.equal(siteSettings({}).indexable, false);
  for (const SITE_URL of ["http://example.com", "https://localhost", "https://127.0.0.1", "https://example.com/path", "https://user:pass@example.com", "https://example.com?x=1"]) {
    assert.throws(() => siteSettings({ SITE_URL, SITE_INDEXABLE: "true" }));
  }
  assert.equal(siteSettings({ SITE_URL: "https://shop.example.com/", SITE_INDEXABLE: "true" }).origin, "https://shop.example.com");
});

test("pagination keeps its own canonical; filters and malformed queries are noindex", () => {
  assert.deepEqual(listingSeo("/shop", { page: "2" }), { path: "/shop?page=2", suffix: " — Page 2", noindex: false });
  assert.equal(listingSeo("/shop", { page: "1" }).path, "/shop");
  for (const query of [{ q: "vase" }, { featured: "true" }, { sort: "newest" }, { page: "0" }, { page: ["1", "2"] }]) {
    assert.equal(listingSeo("/shop", query).noindex, true);
  }
});

test("metadata shares the canonical and explicit noindex survives launch", () => {
  const previous = { url: process.env.SITE_URL, index: process.env.SITE_INDEXABLE };
  try {
    process.env.SITE_URL = "https://shop.example.com";
    process.env.SITE_INDEXABLE = "true";
    const metadata = publicMetadata({ title: "Vases", description: "Ceramic vases for your home.", path: "/categories/vases", noindex: true });
    assert.equal(metadata.alternates?.canonical, "/categories/vases");
    assert.equal((metadata.robots as { index: boolean }).index, false);
    assert.equal(metadata.openGraph?.url, "/categories/vases");
    assert.equal(metadata.openGraph?.description, metadata.description);
  } finally {
    if (previous.url === undefined) delete process.env.SITE_URL; else process.env.SITE_URL = previous.url;
    if (previous.index === undefined) delete process.env.SITE_INDEXABLE; else process.env.SITE_INDEXABLE = previous.index;
  }
});

test("breadcrumbs have ordered positions and absolute URLs", () => {
  const data = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Vases", path: "/categories/vases" }], "https://example.com");
  assert.equal(data.itemListElement[1].position, 2);
  assert.equal(data.itemListElement[1].item, "https://example.com/categories/vases");
});

test("sitemap traverses every catalog page, excludes demos and empty categories", async () => {
  const categories = [{ id: "c", slug: "vases" }, { id: "empty", slug: "empty" }] as Category[];
  const product = { slug: "vase", name: "Vase", category: categories[0] } as Product;
  const calls: number[] = [];
  const paths = await catalogPaths(categories, async (page) => {
    calls.push(page);
    return { pages: 2, items: page === 1 ? [{ ...product, name: "[DEMO] Vase", slug: "demo-vase" }] : [product, product] } as ProductPage;
  });
  assert.deepEqual(calls, [1, 2]);
  assert.deepEqual(paths, ["/", "/shop", "/product/vase", "/categories/vases"]);
  assert.ok(!paths.some((path) => /admin|account|cart|login|wishlist|checkout/.test(path)));
});

test("sitemap fails rather than publishing a partial catalog on API failure", async () => {
  await assert.rejects(catalogPaths([], async () => { throw new Error("API unavailable"); }), /API unavailable/);
  await assert.rejects(catalogPaths([], async () => ({ pages: 938, items: [] }) as unknown as ProductPage), /split sitemaps/);
});

test("private HTTP noindex headers remain enabled when production indexing is on", async () => {
  const previous = process.env.SITE_INDEXABLE;
  try {
    process.env.SITE_INDEXABLE = "true";
    const headers = await nextConfig.headers!();
    for (const source of ["/admin/:path*", "/account/:path*", "/cart", "/wishlist", "/checkout", "/login", "/api/:path*"]) {
      assert.ok(headers.some((rule) => rule.source === source && rule.headers.some((header) => header.key === "X-Robots-Tag" && header.value.includes("noindex"))));
    }
    assert.ok(!headers.some((rule) => rule.source === "/:path*"));
    const redirects = await nextConfig.redirects!();
    assert.ok(redirects.some((rule) => rule.source === "/products/:slug" && rule.destination === "/product/:slug" && rule.permanent));
  } finally {
    if (previous === undefined) delete process.env.SITE_INDEXABLE; else process.env.SITE_INDEXABLE = previous;
  }
});

// Read-only smoke check against the local, non-indexable preview.
import assert from "node:assert/strict";
const base = process.env.SEO_CHECK_URL || "http://127.0.0.1:3000";
async function read(path) {
  const response = await fetch(`${base}${path}`, { redirect: "manual", headers: { "User-Agent": "Googlebot" } });
  return { response, html: await response.text() };
}
for (const path of ["/", "/shop", "/shop?sort=newest", "/shop?q=vase"]) {
  const { response, html } = await read(path);
  assert.equal(response.status, 200, path);
  assert.match(html, /rel="canonical"/, path);
  assert.match(html, /property="og:title"/, path);
  assert.match(html, /name="robots" content="noindex/, path);
}
for (const path of ["/admin", "/admin/reviews", "/account/addresses", "/account/orders", "/cart", "/wishlist", "/checkout", "/login"]) {
  const { response, html } = await read(path);
  assert.match(response.headers.get("x-robots-tag") || "", /noindex/, path);
  assert.match(html, /name="robots" content="noindex/, path);
}
for (const path of ["/does-not-exist-seo-check", "/product/does-not-exist-seo-check", "/categories/does-not-exist-seo-check"]) {
  const { response, html } = await read(path);
  // Streaming may already have sent 200; Next still emits its 404 noindex boundary.
  assert.ok([200, 404].includes(response.status), path);
  assert.match(html, /This corner is still empty/, path);
  assert.match(html, /name="robots" content="noindex/, path);
}
const legacy = await read("/products/does-not-exist-seo-check");
assert.equal(legacy.response.status, 308);
assert.equal(new URL(legacy.response.headers.get("location"), base).pathname, "/product/does-not-exist-seo-check");
const robots = await read("/robots.txt");
assert.equal(robots.response.status, 200);
assert.match(robots.html, /Disallow: \/\s/);
const sitemap = await read("/sitemap.xml");
assert.equal(sitemap.response.status, 200);
assert.ok(!sitemap.html.includes("<loc>"), "Local preview must have an empty sitemap");
const catalog = await fetch(`${base}/api/v1/products?page_size=1`).then((response) => response.json());
if (catalog.items?.length) {
  const product = catalog.items[0];
  for (const path of [`/product/${product.slug}`, `/categories/${product.category.slug}`]) {
    const { response, html } = await read(path);
    assert.equal(response.status, 200, path);
    assert.ok(html.includes(`href="${base}${path}"`), `Canonical missing: ${path}`);
    assert.match(html, /BreadcrumbList/, path);
    assert.match(html, /property="og:description"/, path);
    assert.equal((html.match(/<main[ >]/g) || []).length, 1, path);
    if (path.startsWith("/product/") && product.name.startsWith("[DEMO]")) {
      assert.ok(!html.includes('"@type":"Product"'), "Demo products must not publish rich-result offers");
    }
  }
}
console.log("SEO smoke checks passed: public metadata, private noindex, missing routes, 308 redirect, staging robots and sitemap.");

import test from "node:test";
import assert from "node:assert/strict";
import { productJsonLd, serializeJsonLd } from "../src/lib/product-seo.ts";
import type { Product } from "../src/lib/catalog.ts";
const product = {
  name: "Vase </script><script>alert(1)</script>",
  slug: "vase",
  description: "Ceramic",
  images: [],
  variants: [{ sku: "VASE", label: "Sand", price: "800.00", in_stock: false }],
  rating: null,
  review_count: 0,
} as unknown as Product;
test("JSON-LD cannot escape its script element", () => {
  const encoded = serializeJsonLd(
    productJsonLd(product, "https://example.com"),
  );
  assert.ok(!encoded.includes("<"));
  assert.equal(JSON.parse(encoded).name, product.name);
});
test("uses canonical URL and genuine stock, omits absent rating", () => {
  const json = productJsonLd(product, "https://example.com");
  assert.equal(json.url, "https://example.com/product/vase");
  assert.equal(json.offers[0].availability, "https://schema.org/OutOfStock");
  assert.equal(json.offers[0].price, "800.00");
  assert.equal(json.offers[0].priceCurrency, "INR");
  assert.ok(!("aggregateRating" in json));
});
test("includes only the API rating when reviews exist", () => {
  const json = productJsonLd(
    { ...product, rating: 4.5, review_count: 2 },
    "https://example.com",
  );
  assert.equal(json.aggregateRating?.reviewCount, 2);
  assert.equal(json.aggregateRating?.ratingValue, 4.5);
});

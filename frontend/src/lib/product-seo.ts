import type { Product } from "./catalog";
import { imageSource } from "./media.ts";
export function productJsonLd(p: Product, base: string) {
  const url = new URL(`/product/${p.slug}`, base).href;
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    "@id": `${url}#product`,
    name: p.name,
    url,
    description: p.description,
    ...(p.images.length
      ? { image: p.images.map((i) => new URL(imageSource(i.url), base).href) }
      : {}),
    ...(p.variants.length === 1 ? { sku: p.variants[0].sku } : {}),
    offers: p.variants.map((v) => ({
      "@type": "Offer",
      url,
      sku: v.sku,
      name: v.label,
      priceCurrency: "INR",
      price: v.price,
      availability: `https://schema.org/${v.in_stock ? "InStock" : "OutOfStock"}`,
    })),
    ...(p.review_count > 0 && p.rating !== null
      ? {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: p.rating,
            reviewCount: p.review_count,
          },
        }
      : {}),
  };
}
export const serializeJsonLd = (value: unknown) =>
  JSON.stringify(value).replace(/</g, "\\u003c");

import Link from "next/link";
import { notFound } from "next/navigation";
import { api, ApiError, Product, ProductPage } from "@/lib/catalog";
import { productJsonLd, serializeJsonLd } from "@/lib/product-seo";
import ProductGallery from "@/components/product-gallery";
import ProductPurchase from "@/components/product-purchase";
import ProductGrid from "@/components/product-grid";
import ProductReviewForm from "@/components/product-review-form";
import { imageSource, isDemo, productName } from "@/lib/media";
import { breadcrumbJsonLd, publicMetadata, siteSettings } from "@/lib/seo";
type Reviews = {
  items: {
    id: string;
    author: string;
    body: string;
    rating: number;
    created_at: string;
  }[];
  total: number;
  page: number;
  pages: number;
};
async function getProduct(slug: string) {
  try {
    return await api<Product>(`/products/slug/${encodeURIComponent(slug)}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}
export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ reviews?: string }>;
}) {
  const p = await getProduct((await params).slug);
  const title = p.seo_title || p.name;
  const description = p.seo_description || p.description.slice(0, 160) || `Explore ${p.name} at Your Sanctuary.`;
  return publicMetadata({ title, description, path: `/product/${p.slug}`,
    ...(p.images.length ? { images: p.images.slice(0, 1).map((i) => ({ url: imageSource(i.url), alt: i.alt || p.name })) } : {}),
    noindex: isDemo(p.name) || Boolean((await searchParams).reviews),
  });
}
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ reviews?: string }>;
}) {
  const p = await getProduct((await params).slug);
  const raw = (await searchParams).reviews;
  const page = raw && /^[1-9]\d{0,3}$/.test(raw) ? Number(raw) : 1;
  const [reviews, related] = await Promise.allSettled([
    api<Reviews>(`/products/${p.id}/reviews?page=${page}`),
    api<ProductPage>(
      `/products?category=${encodeURIComponent(p.category.slug)}&page_size=5`,
    ),
  ]);
  const relatedItems =
    related.status === "fulfilled"
      ? related.value.items.filter((item) => item.id !== p.id).slice(0, 4)
      : [];
  return (
    <>
      {!isDemo(p.name) && <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: serializeJsonLd(
            productJsonLd(p, siteSettings().origin),
          ),
        }}
      />}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(breadcrumbJsonLd([
        { name: "Home", path: "/" }, { name: "Shop", path: "/shop" },
        { name: p.category.name, path: `/categories/${p.category.slug}` },
        { name: productName(p.name), path: `/product/${p.slug}` },
      ], siteSettings().origin)) }} />
      <section className="wrap pdp">
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          <Link href="/">Home</Link> /{" "}
          <Link href="/shop">Shop</Link> /{" "}
          <Link href={`/categories/${p.category.slug}`}>{p.category.name}</Link>{" "}
          / <span>{productName(p.name)}</span>
        </nav>
        <div className="pdp-grid">
          <ProductGallery images={p.images} name={p.name} />
          <div className="pdp-summary">
            <p className="eyebrow">{p.category.name} / The considered home</p>
            <h1>{productName(p.name)}</h1>
            {isDemo(p.name) && (
              <p className="demo-notice">
                Demo collection · AI-created imagery and sample pricing. For
                preview only.
              </p>
            )}
            <a href="#reviews" className="review-link">
              {p.review_count > 0
                ? `★ ${p.rating} · ${p.review_count} customer reviews`
                : "No reviews yet"}
            </a>
            <p className="pdp-intro">{p.description.split("\n\n")[0]}</p>
            <ProductPurchase product={p} />
          </div>
        </div>
        <div className="product-information">
          <section>
            <p className="eyebrow">A closer look</p>
            <h2>Made for your space.</h2>
            <p className="preserve-text">
              {p.description || "Product description coming soon."}
            </p>
          </section>
          <section>
            <h2>The details</h2>
            {Object.keys(p.specifications).length ? (
              <dl className="specs">
                {Object.entries(p.specifications).map(([k, v]) => (
                  <div className="contents" key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="muted">Specifications will be added soon.</p>
            )}
          </section>
        </div>
        <section id="reviews" className="reviews-section">
          <p className="eyebrow">In your words</p>
          <h2>Customer reviews</h2>
          <ProductReviewForm productId={p.id} />
          {reviews.status === "rejected" ? (
            <p>Reviews could not be loaded. Please refresh to try again.</p>
          ) : (
            <>
              {reviews.value.items.length ? (
                reviews.value.items.map((r) => (
                  <article className="review-card" key={r.id}>
                    <div>
                      <strong>{r.author}</strong>
                      <span aria-label={`${r.rating} out of 5 stars`}>
                        {"★".repeat(r.rating)}
                        {"☆".repeat(5 - r.rating)}
                      </span>
                      <time dateTime={r.created_at}>
                        {new Intl.DateTimeFormat("en-IN", {
                          month: "short",
                          year: "numeric",
                          timeZone: "Asia/Kolkata",
                        }).format(new Date(r.created_at))}
                      </time>
                    </div>
                    <p className="preserve-text">{r.body}</p>
                  </article>
                ))
              ) : (
                <p className="muted">
                  {reviews.value.total
                    ? "No reviews on this page."
                    : "No customer reviews yet. Published reviews will appear here."}
                </p>
              )}
              {reviews.value.pages > 1 && (
                <nav className="pagination" aria-label="Review pages">
                  {page > 1 && (
                    <Link href={`?reviews=${page - 1}#reviews`}>
                      ← Previous
                    </Link>
                  )}
                  <span>
                    Page {page} of {reviews.value.pages}
                  </span>
                  {page < reviews.value.pages && (
                    <Link href={`?reviews=${page + 1}#reviews`}>Next →</Link>
                  )}
                </nav>
              )}
            </>
          )}
        </section>
        {relatedItems.length > 0 && (
          <section className="section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Better together</p>
                <h2>You may also like</h2>
              </div>
              <Link href={`/categories/${p.category.slug}`}>
                Explore {p.category.name} ↗
              </Link>
            </div>
            <ProductGrid products={relatedItems} />
          </section>
        )}
      </section>
    </>
  );
}

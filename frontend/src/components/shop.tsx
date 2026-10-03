import Link from "next/link";
import Image from "next/image";
import { imageSource } from "@/lib/media";
import { api, ApiError, Category, ProductPage } from "@/lib/catalog";
import ProductGrid from "./product-grid";
import CatalogUnavailable from "./catalog-unavailable";
import ResponsiveFilters from "./responsive-filters";
import { notFound } from "next/navigation";
export type Search = Record<string, string | string[] | undefined>;
const allowed = [
  "q",
  "category",
  "min_price",
  "max_price",
  "sort",
  "page",
  "in_stock",
  "on_sale",
];
export default async function Shop({
  search,
  category,
}: {
  search: Search;
  category?: Category;
}) {
  const params = new URLSearchParams();
  for (const key of allowed) {
    const value = search[key];
    if (typeof value === "string" && value) params.set(key, value);
  }
  if (category) params.set("category", category.slug);
  let categories: Category[];
  let result: ProductPage;
  try {
    [categories, result] = await Promise.all([
      api<Category[]>("/categories"),
      api<ProductPage>(`/products?${params}`),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 422)
      return (
        <section className="wrap section">
          <h1>Check your filters</h1>
          <p>
            Use positive prices, a valid page number and a minimum price below
            the maximum.
          </p>
          <Link
            className="button button-primary"
            href={category ? `/categories/${category.slug}` : "/shop"}
          >
            Reset filters
          </Link>
        </section>
      );
    // A backend outage is an expected recoverable state, not a rendering failure.
    return <CatalogUnavailable />;
  }
  const path = category ? `/categories/${category.slug}` : "/shop";
  const offersOnly = params.get("on_sale") === "true";
  const resetPath = offersOnly ? `${path}?on_sale=true` : path;
  if (result.page > 1 && result.page > result.pages) notFound();
  const pageLink = (page: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(page));
    if (category) next.delete("category");
    return `${path}?${next}`;
  };
  return (
    <>
      <section className="shop-banner">
        {result.items[0]?.images[0] && (
          <Image
            src={imageSource(result.items[0].images[0].url)}
            alt=""
            fill
            sizes="100vw"
          />
        )}
        <div className="wrap shop-intro">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <Link href="/">Home</Link> / <Link href="/shop">Shop</Link>
            {category && ` / ${category.name}`}
          </nav>
          <p className="eyebrow">Find something that feels like you</p>
          <h1>
            {category?.name ||
              (params.get("on_sale") === "true"
                ? "Offers"
                : params.get("sort") === "newest"
                  ? "New arrivals"
                  : "The collection")}
          </h1>
          <p className="muted">
            {offersOnly ? "Only reduced-price pieces, with savings based on the displayed compare-at price." : category?.description ||
              "Beautiful details for the rooms you love."}
          </p>
        </div>
      </section>
      <div className="wrap shop-layout">
        <aside aria-label="Product filters">
          <ResponsiveFilters>
            <form key={params.toString()} action={path} className="filters">
              <label>
                Search
                <input
                  className="input"
                  name="q"
                  type="search"
                  maxLength={100}
                  defaultValue={params.get("q") || ""}
                  placeholder="Try ceramic vase"
                />
              </label>
              {!category && (
                <label>
                  Category
                  <select
                    className="input"
                    name="category"
                    defaultValue={params.get("category") || ""}
                  >
                    <option value="">All categories</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.slug}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                Minimum price (₹)
                <input
                  className="input"
                  type="number"
                  name="min_price"
                  min="0"
                  step="0.01"
                  defaultValue={params.get("min_price") || ""}
                />
              </label>
              <label>
                Maximum price (₹)
                <input
                  className="input"
                  type="number"
                  name="max_price"
                  min="0"
                  step="0.01"
                  defaultValue={params.get("max_price") || ""}
                />
              </label>
              <label>
                Sort by
                <select
                  className="input"
                  name="sort"
                  defaultValue={params.get("sort") || "newest"}
                >
                  <option value="newest">Newest arrivals</option>
                  <option value="price_asc">Price: low to high</option>
                  <option value="price_desc">Price: high to low</option>
                  <option value="name">Name: A to Z</option>
                  <option value="best_sellers">Best sellers</option>
                </select>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="in_stock"
                  value="true"
                  defaultChecked={params.get("in_stock") === "true"}
                />{" "}
                In stock only
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="on_sale"
                  value="true"
                  defaultChecked={params.get("on_sale") === "true"}
                />{" "}
                Offers only
              </label>
              <button className="button button-primary" type="submit">
                Apply filters
              </button>
              <Link href={resetPath}>Clear filters</Link>
            </form>
          </ResponsiveFilters>
        </aside>
        <section aria-label="Products">
          <p className="results-meta">
            {result.total} {result.total === 1 ? "piece" : "pieces"}
            {params.get("q") && ` for “${params.get("q")}”`}
          </p>
          {result.items.length > 0 ? (
            <ProductGrid products={result.items} />
          ) : (
            <div className="empty-note">
              <h2>{offersOnly ? "No offers match right now." : "Room for something new."}</h2>
              <p>
                {offersOnly ? "Try adjusting your filters or check back for reduced-price pieces." : "No pieces match these filters right now. Try a different search or explore the full collection."}
              </p>
              <Link href={resetPath}>Reset filters ↗</Link>
            </div>
          )}
          {result.pages > 1 && (
            <nav className="pagination" aria-label="Pagination">
              {result.page > 1 && (
                <Link href={pageLink(result.page - 1)}>← Previous</Link>
              )}
              <span>
                Page {result.page} of {result.pages}
              </span>
              {result.page < result.pages && (
                <Link href={pageLink(result.page + 1)}>Next →</Link>
              )}
            </nav>
          )}
        </section>
      </div>
    </>
  );
}

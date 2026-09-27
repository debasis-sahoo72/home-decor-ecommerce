"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { money } from "@/lib/catalog";
import { readApi, PageData, orderDate } from "@/lib/orders";
import { request } from "@/lib/shopping-client";
import ProductMedia from "./product-media";

type Category = {
  id: string;
  name: string;
  slug: string;
  description: string;
  active: boolean;
  seo_title: string | null;
  seo_description: string | null;
};
type Variant = {
  id: string;
  sku: string;
  label: string;
  price: string;
  compare_at_price: string | null;
  active: boolean;
};
type Product = {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: Category;
  active: boolean;
  featured: boolean;
  seo_title: string | null;
  seo_description: string | null;
  specifications: Record<string, string>;
  variants: Variant[];
};
type Row = {
  id?: string;
  pincode?: string;
  name?: string;
  sku?: string;
  email?: string;
  status?: string;
  on_hand?: number;
  reserved?: number;
  available?: number;
  active?: boolean;
  urban?: boolean;
  min_days?: number;
  max_days?: number;
  cutoff_hour?: number;
  fee?: string;
  product_name?: string;
  rating?: number;
  body?: string;
  created_at?: string;
};
type Metrics = {
  orders_today: number;
  revenue_today: string;
  pending_orders: number;
  low_stock_products: number;
  date: string;
};

function Input({
  name,
  label,
  value,
  type = "text",
  required = true,
  maxLength,
  min,
  max,
  step,
}: {
  name: string;
  label: string;
  value?: string | number | null;
  type?: string;
  required?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
  step?: string;
}) {
  return (
    <label>
      {label}
      <input
        name={name}
        defaultValue={value ?? ""}
        type={type}
        required={required}
        maxLength={maxLength}
        min={min}
        max={max}
        step={step}
      />
    </label>
  );
}
function Check({
  name,
  label,
  value,
}: {
  name: string;
  label: string;
  value?: boolean;
}) {
  return (
    <label className="ops-check">
      <input name={name} type="checkbox" defaultChecked={value} />
      {label}
    </label>
  );
}
const text = (f: FormData, k: string) => String(f.get(k) || "");
const nullable = (f: FormData, k: string) => text(f, k) || null;

export default function AdminPanel({ section }: { section: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<
    Product | Category | Row | "new" | null
  >(null);
  useEffect(() => {
    const c = new AbortController();
    async function load() {
      try {
        if (section === "dashboard") {
          const value = await readApi<Metrics>("/admin/dashboard", c.signal);
          if (!c.signal.aborted) setMetrics(value);
        } else if (section === "categories") {
          const value = await readApi<Category[]>(
            "/admin/categories",
            c.signal,
          );
          if (!c.signal.aborted) {
            setCategories(value);
            setPages(1);
          }
        } else {
          const params = new URLSearchParams({ page: String(page) });
          if (query) params.set("q", query);
          if (section === "reviews" && filter) params.set("status", filter);
          if (section === "inventory" && filter) params.set("low_only", "true");
          if (section === "products") {
            const [data, cats] = await Promise.all([
              readApi<PageData<Product>>(`/admin/catalog?${params}`, c.signal),
              readApi<Category[]>("/admin/categories", c.signal),
            ]);
            if (!c.signal.aborted) {
              setProducts(data.items);
              setCategories(cats);
              setPages(data.pages);
            }
          } else {
            const data = await readApi<PageData<Row>>(
              `/admin/${section}?${params}`,
              c.signal,
            );
            if (!c.signal.aborted) {
              setRows(data.items);
              setPages(data.pages);
            }
          }
        }
        if (!c.signal.aborted) setError("");
      } catch (e) {
        if (!c.signal.aborted)
          setError(e instanceof Error ? e.message : "Unable to load data.");
      } finally {
        if (!c.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => c.abort();
  }, [section, page, query, filter, revision]);
  async function mutate(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      setEditing(null);
      setNotice("Changes saved.");
      setRevision((v) => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save.");
    } finally {
      setBusy(false);
    }
  }
  const title =
    section === "delivery"
      ? "Delivery PIN codes"
      : section[0].toUpperCase() + section.slice(1);
  const product =
    editing && editing !== "new" && "variants" in editing
      ? (editing as Product)
      : undefined;
  const category =
    editing && editing !== "new" && section === "categories"
      ? (editing as Category)
      : undefined;
  const pin =
    editing && editing !== "new" && section === "delivery"
      ? (editing as Row)
      : undefined;
  return (
    <>
      <div className="ops-heading">
        <h1>{title}</h1>
        {["products", "categories", "delivery"].includes(section) && (
          <button
            className="button button-primary"
            onClick={() => setEditing("new")}
          >
            + Add{" "}
            {section === "products"
              ? "product"
              : section === "categories"
                ? "category"
                : "PIN code"}
          </button>
        )}
      </div>
      <p className="ops-error" role="alert">
        {error}
      </p>
      <p role="status">{notice}</p>
      {error && (
        <button
          onClick={() => {
            setLoading(true);
            setRevision((v) => v + 1);
          }}
        >
          Retry loading
        </button>
      )}
      {section !== "dashboard" && section !== "categories" && (
        <form
          className="ops-filters"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            setQuery(text(f, "q"));
            setFilter(text(f, "filter"));
            setPage(1);
            setLoading(true);
            setRevision((v) => v + 1);
          }}
        >
          {section !== "reviews" && (
            <label>
              Search
              <input
                name="q"
                placeholder={section === "delivery" ? "PIN code" : "Search"}
                maxLength={section === "delivery" ? 6 : 100}
                pattern={section === "delivery" ? "[0-9]*" : undefined}
              />
            </label>
          )}
          {section === "inventory" && (
            <label>
              Stock
              <select name="filter">
                <option value="">All stock</option>
                <option value="low">Low stock (5 or fewer)</option>
              </select>
            </label>
          )}
          {section === "reviews" && (
            <label>
              Status
              <select name="filter">
                <option value="">All reviews</option>
                <option>pending</option>
                <option>published</option>
                <option>rejected</option>
              </select>
            </label>
          )}
          <button className="button button-secondary">Apply</button>
        </form>
      )}
      {editing && (
        <section
          className="ops-card ops-editor"
          key={
            typeof editing === "string"
              ? editing
              : editing.id ||
                ("pincode" in editing ? editing.pincode : undefined)
          }
        >
          <div className="ops-heading">
            <h2>
              {editing === "new" ? "Add" : "Edit"}{" "}
              {section === "products"
                ? "product"
                : section === "categories"
                  ? "category"
                  : "PIN code"}
            </h2>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => setEditing(null)}
            >
              Close editor
            </button>
          </div>
          {section !== "delivery" ? (
            <form
              className="ops-form"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const body = {
                  name: text(f, "name"),
                  slug: text(f, "slug"),
                  description: text(f, "description"),
                  active: f.has("active"),
                  seo_title: nullable(f, "seo_title"),
                  seo_description: nullable(f, "seo_description"),
                };
                void mutate(async () => {
                  if (section === "products") {
                    const specs: Record<string, string> = {};
                    for (const line of text(f, "specifications")
                      .split("\n")
                      .filter((x) => x.trim())) {
                      const split = line.indexOf(":");
                      if (split < 1)
                        throw new Error(
                          "Use Material: Ceramic for each specification line.",
                        );
                      specs[line.slice(0, split).trim()] = line
                        .slice(split + 1)
                        .trim();
                    }
                    return request(
                      `/admin/products${product ? `/${product.id}` : ""}`,
                      {
                        ...body,
                        category_id: text(f, "category_id"),
                        featured: f.has("featured"),
                        specifications: specs,
                      },
                      product ? "PUT" : "POST",
                    );
                  }
                  return request(
                    `/admin/categories${category ? `/${category.id}` : ""}`,
                    body,
                    category ? "PUT" : "POST",
                  );
                });
              }}
            >
              <Input
                name="name"
                label="Name"
                value={product?.name || category?.name}
                maxLength={section === "products" ? 200 : 100}
              />
              <Input
                name="slug"
                label="URL slug (lowercase, hyphen-separated)"
                value={product?.slug || category?.slug}
                maxLength={120}
              />
              {section === "products" && (
                <label>
                  Category
                  <select
                    name="category_id"
                    defaultValue={product?.category.id}
                    required
                  >
                    <option value="">Select a category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="wide">
                Description
                <textarea
                  name="description"
                  defaultValue={product?.description || category?.description}
                  maxLength={section === "products" ? 8000 : 4000}
                />
              </label>
              {section === "products" && (
                <label className="wide">
                  Specifications (one Name: Value per line)
                  <textarea
                    name="specifications"
                    defaultValue={Object.entries(product?.specifications || {})
                      .map(([k, v]) => `${k}: ${v}`)
                      .join("\n")}
                  />
                </label>
              )}
              <Input
                name="seo_title"
                label="SEO title"
                value={product?.seo_title || category?.seo_title}
                required={false}
                maxLength={70}
              />
              <Input
                name="seo_description"
                label="SEO description"
                value={product?.seo_description || category?.seo_description}
                required={false}
                maxLength={160}
              />
              <Check
                name="active"
                label="Active"
                value={product?.active ?? category?.active ?? false}
              />
              {section === "products" && (
                <Check
                  name="featured"
                  label="Featured collection"
                  value={product?.featured}
                />
              )}
              <div className="wide">
                <button className="button button-primary" disabled={busy}>
                  {busy ? "Saving…" : "Save"}
                </button>
                {section === "products" && !product && (
                  <p className="muted">
                    New products start inactive. After saving, edit the product
                    to add a SKU and price. Stock is managed in Inventory.
                  </p>
                )}
              </div>
            </form>
          ) : (
            <form
              className="ops-form"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                void mutate(() =>
                  request(
                    `/admin/delivery/${text(f, "pincode")}`,
                    {
                      service: "standard",
                      active: f.has("active"),
                      urban: f.has("urban"),
                      min_days: Number(f.get("min_days")),
                      max_days: Number(f.get("max_days")),
                      cutoff_hour: Number(f.get("cutoff_hour")),
                      fee: text(f, "fee"),
                    },
                    "PUT",
                  ),
                );
              }}
            >
              <label>
                PIN code
                <input
                  name="pincode"
                  defaultValue={pin?.pincode}
                  readOnly={!!pin}
                  required
                  pattern="[1-9][0-9]{5}"
                  maxLength={6}
                />
              </label>
              <Input
                name="fee"
                label="Delivery fee (₹)"
                value={pin?.fee ?? "0.00"}
                type="number"
                min={0}
                max={10000}
                step="0.01"
              />
              <Input
                name="min_days"
                label="Minimum calendar days"
                value={pin?.min_days ?? 3}
                type="number"
                min={2}
                max={60}
              />
              <Input
                name="max_days"
                label="Maximum calendar days"
                value={pin?.max_days ?? 5}
                type="number"
                min={2}
                max={60}
              />
              <Input
                name="cutoff_hour"
                label="Cutoff hour (India time, 0–23)"
                value={pin?.cutoff_hour ?? 12}
                type="number"
                min={0}
                max={23}
              />
              <Check
                name="urban"
                label="Verified urban coverage"
                value={pin?.urban}
              />
              <Check
                name="active"
                label="Enable standard delivery"
                value={pin?.active}
              />
              <button className="button button-primary" disabled={busy}>
                Save PIN code
              </button>
              <p className="wide muted">
                Enable only PIN codes your delivery operation supports. All
                locations use standard delivery.
              </p>
            </form>
          )}
          {product && (
            <>
              <h3>Variants and prices</h3>
              {[...product.variants, undefined].map((v, n) => (
                <form
                  className="ops-form ops-card"
                  key={v?.id || "new"}
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    void mutate(() =>
                      request(
                        v
                          ? `/admin/variants/${v.id}`
                          : `/admin/products/${product.id}/variants`,
                        {
                          sku: text(f, "sku"),
                          label: text(f, "label"),
                          price: text(f, "price"),
                          compare_at_price: nullable(f, "compare_at_price"),
                          active: f.has("active"),
                        },
                        v ? "PUT" : "POST",
                      ),
                    );
                  }}
                >
                  <h3 className="wide">{v ? v.sku : "Add SKU"}</h3>
                  <Input name="sku" label="SKU" value={v?.sku} maxLength={80} />
                  <Input
                    name="label"
                    label="Variant name"
                    value={v?.label}
                    maxLength={100}
                  />
                  <Input
                    name="price"
                    label="Price (₹)"
                    type="number"
                    value={v?.price}
                    min={0}
                    step="0.01"
                  />
                  <Input
                    name="compare_at_price"
                    label="Compare-at price (₹, optional)"
                    type="number"
                    value={v?.compare_at_price}
                    min={0}
                    step="0.01"
                    required={false}
                  />
                  <Check
                    name="active"
                    label="Active variant"
                    value={v?.active ?? true}
                  />
                  <button className="button button-primary" disabled={busy}>
                    {n < product.variants.length ? "Save SKU" : "Add SKU"}
                  </button>
                </form>
              ))}
              <ProductMedia productId={product.id} />
            </>
          )}
        </section>
      )}
      {loading ? (
        <p role="status">Loading {title.toLowerCase()}…</p>
      ) : (
        <>
          {section === "dashboard" && metrics && (
            <>
              <p>Today in India · {metrics.date}</p>
              <div className="ops-metrics">
                {[
                  [
                    "Orders today",
                    String(metrics.orders_today),
                    "All orders created today",
                  ],
                  [
                    "Revenue today",
                    money(metrics.revenue_today),
                    "Gross captured payments today",
                  ],
                  [
                    "Pending orders",
                    String(metrics.pending_orders),
                    "Awaiting payment or dispatch",
                  ],
                  [
                    "Low stock products",
                    String(metrics.low_stock_products),
                    "Active products with ≤5 available",
                  ],
                ].map(([label, value, note]) => (
                  <div className="ops-card" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                    <small>{note}</small>
                  </div>
                ))}
              </div>
              <section className="ops-card">
                <h2>Daily operations</h2>
                <div className="ops-actions">
                  <Link className="button button-primary" href="/admin/orders">
                    Review orders
                  </Link>
                  <Link
                    className="button button-secondary"
                    href="/admin/inventory"
                  >
                    Check inventory
                  </Link>
                  <Link
                    className="button button-secondary"
                    href="/admin/delivery"
                  >
                    Manage delivery coverage
                  </Link>
                </div>
                <p className="muted">
                  Payment confirmation and refunds will be connected in the
                  Razorpay phase.
                </p>
              </section>
            </>
          )}
          {section === "products" && (
            <div className="ops-table-wrap">
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Category</th>
                    <th>SKUs</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id}>
                      <td>
                        {p.name}
                        <small>{p.slug}</small>
                      </td>
                      <td>{p.category.name}</td>
                      <td>{p.variants.length}</td>
                      <td>{p.active ? "Active" : "Inactive"}</td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => setEditing(p)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!products.length && (
                <p className="ops-card">No matching products.</p>
              )}
            </div>
          )}
          {section === "categories" && (
            <div className="ops-table-wrap">
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Slug</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((c) => (
                    <tr key={c.id}>
                      <td>{c.name}</td>
                      <td>{c.slug}</td>
                      <td>{c.active ? "Active" : "Inactive"}</td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => setEditing(c)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!categories.length && (
                <p className="ops-card">No categories yet.</p>
              )}
            </div>
          )}
          {section === "inventory" && (
            <div className="ops-table-wrap">
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Product / SKU</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>On hand</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td>
                        {r.name}
                        <small>{r.sku}</small>
                      </td>
                      <td>{r.reserved}</td>
                      <td>{r.available}</td>
                      <td>
                        <form
                          className="ops-inline"
                          key={`${r.id}-${r.on_hand}`}
                          onSubmit={(e) => {
                            e.preventDefault();
                            const f = new FormData(e.currentTarget);
                            void mutate(() =>
                              request(
                                `/admin/variants/${r.id}/stock`,
                                { on_hand: Number(f.get("stock")) },
                                "PUT",
                              ),
                            );
                          }}
                        >
                          <input
                            aria-label={`On-hand stock for ${r.sku}`}
                            name="stock"
                            type="number"
                            min={r.reserved}
                            max={2000000000}
                            defaultValue={r.on_hand}
                            required
                          />
                          <button className="text-button" disabled={busy}>
                            Save
                          </button>
                        </form>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {section === "customers" && (
            <div className="ops-table-wrap">
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td>{r.name}</td>
                      <td>{r.email}</td>
                      <td>{r.status}</td>
                      <td>{r.created_at && orderDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {section === "delivery" && (
            <div className="ops-table-wrap">
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>PIN</th>
                    <th>Standard estimate</th>
                    <th>Fee</th>
                    <th>Coverage</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.pincode}>
                      <td>{r.pincode}</td>
                      <td>
                        {r.min_days}–{r.max_days} days
                      </td>
                      <td>{money(r.fee || "0")}</td>
                      <td>
                        {r.active && r.urban ? "Enabled urban" : "Unavailable"}
                      </td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => setEditing(r)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {section === "reviews" && (
            <div className="ops-grid">
              {rows.map((r) => (
                <article className="ops-card" key={r.id}>
                  <h2>{r.product_name}</h2>
                  <p>
                    {r.rating}/5 · {r.status}
                  </p>
                  <p>{r.body}</p>
                  <div className="ops-actions">
                    {["pending", "published", "rejected"].map((s) => (
                      <button
                        className="button button-secondary"
                        disabled={busy || s === r.status}
                        key={s}
                        onClick={() =>
                          void mutate(() =>
                            request(
                              `/admin/reviews/${r.id}`,
                              { status: s },
                              "PATCH",
                            ),
                          )
                        }
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
          {["inventory", "customers", "delivery", "reviews"].includes(
            section,
          ) &&
            rows.length === 0 && (
              <p className="empty-note">No matching records.</p>
            )}
          {!["categories", "dashboard"].includes(section) && pages > 0 && (
            <div className="ops-pagination">
              <button
                disabled={page <= 1}
                onClick={() => {
                  setPage(page - 1);
                  setLoading(true);
                }}
              >
                Previous
              </button>
              <span>
                Page {page} of {pages}
              </span>
              <button
                disabled={page >= pages}
                onClick={() => {
                  setPage(page + 1);
                  setLoading(true);
                }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}

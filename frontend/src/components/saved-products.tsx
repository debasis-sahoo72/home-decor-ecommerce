"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Product } from "@/lib/catalog";
import ProductGrid from "./product-grid";
import { useSaved } from "./wishlist-button";
export default function SavedProducts() {
  const ids = useSaved();
  const key = ids.join(",");
  const [state, setState] = useState<{
    key: string;
    products: Product[];
    error: boolean;
  }>({ key: "", products: [], error: false });
  useEffect(() => {
    const controller = new AbortController();
    const saved = key ? key.split(",") : [];
    async function load() {
      try {
        const products: Product[] = []; // Bound requests to avoid a burst for large saved lists.
        for (let i = 0; i < saved.length; i += 6) {
          const batch = await Promise.all(
            saved.slice(i, i + 6).map(async (id) => {
              const r = await fetch(`/api/v1/products/${id}`, {
                signal: controller.signal,
              });
              if (r.status === 404) return null;
              if (!r.ok) throw new Error("Unavailable");
              return r.json() as Promise<Product>;
            }),
          );
          products.push(...batch.filter((p): p is Product => p !== null));
        }
        if (!controller.signal.aborted)
          setState({ key, products, error: false });
      } catch {
        if (!controller.signal.aborted)
          setState({ key, products: [], error: true });
      }
    }
    void load();
    return () => controller.abort();
  }, [key]);
  if (state.key !== key) return <p role="status">Loading saved pieces…</p>;
  if (state.error)
    return (
      <p role="alert">
        We could not load your saved pieces. Refresh this page to try again.
      </p>
    );
  return state.products.length ? (
    <ProductGrid products={state.products} />
  ) : (
    <div className="empty-note">
      <h2>Keep a little inspiration.</h2>
      <p>
        Tap the heart on a product to save it here. Unavailable products are
        hidden.
      </p>
      <Link href="/shop">Explore the collection ↗</Link>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Product } from "@/lib/catalog";
import ProductCard from "./product-card";
import { useShopping } from "./shopping-provider";
import { request } from "@/lib/shopping-client";
function SavedCard({ product }: { product: Product }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const variant = product.variants[0];
  return (
    <div className="saved-card">
      <ProductCard product={product} />
      {product.variants.length === 1 ? (
        <button
          className="button button-secondary"
          disabled={busy || !variant?.in_stock}
          onClick={async () => {
            setBusy(true);
            try {
              await request("/cart/items", {
                variant_id: variant.id,
                quantity: 1,
              });
              setMessage("Added to your bag.");
            } catch (e) {
              setMessage(e instanceof Error ? e.message : "Please retry.");
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Adding…" : variant?.in_stock ? "Add to bag" : "Out of stock"}
        </button>
      ) : (
        <Link
          className="button button-secondary"
          href={`/product/${product.slug}`}
        >
          Choose an option
        </Link>
      )}
      <p role="status" className="saved-message">
        {message}{" "}
        {message === "Added to your bag." && (
          <Link href="/cart">View bag →</Link>
        )}
      </p>
    </div>
  );
}
export default function SavedProducts() {
  const { ids, account, ready, error, toggle, refresh, busy } = useShopping();
  const key = ids.join(",");
  const [state, setState] = useState<{
    key: string;
    products: Product[];
    unavailable: string[];
    error: boolean;
  }>({ key: "", products: [], unavailable: [], error: false });
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const products: Product[] = [],
          unavailable: string[] = [];
        const saved = key ? key.split(",") : [];
        for (let i = 0; i < saved.length; i += 6) {
          const batch = await Promise.all(
            saved.slice(i, i + 6).map(async (id) => {
              const r = await fetch(`/api/v1/products/${id}`, {
                signal: controller.signal,
                cache: "no-store",
              });
              if (r.status === 404) {
                unavailable.push(id);
                return null;
              }
              if (!r.ok) throw new Error("Unavailable");
              return r.json() as Promise<Product>;
            }),
          );
          products.push(...batch.filter((p): p is Product => p !== null));
        }
        if (!controller.signal.aborted)
          setState({ key, products, unavailable, error: false });
      } catch {
        if (!controller.signal.aborted)
          setState({ key, products: [], unavailable: [], error: true });
      }
    }
    void load();
    return () => controller.abort();
  }, [key]);
  return (
    <>
      <p className="wishlist-intro muted">
        {account ? (
          "Your favourite pieces, saved to your account across devices."
        ) : (
          <>
            Saved on this device. <Link href="/login">Sign in</Link> to keep
            your wishlist across devices.
          </>
        )}
      </p>
      {error && (
        <p className="field-error" role="alert">
          {error}{" "}
          <button className="text-button" onClick={refresh}>
            Retry
          </button>
        </p>
      )}
      {(!ready || state.key !== key) && !error ? (
        <p role="status">Loading saved pieces…</p>
      ) : state.error ? (
        <p role="alert">
          We could not load your saved pieces. Refresh this page to retry.
        </p>
      ) : (
        <>
          {state.products.length ? (
            <div className="product-grid">
              {state.products.map((p) => (
                <SavedCard key={p.id} product={p} />
              ))}
            </div>
          ) : (
            !ids.length && (
              <div className="empty-note">
                <p className="empty-symbol" aria-hidden="true">
                  ♡
                </p>
                <h2>Keep a little inspiration.</h2>
                <p>
                  Tap the heart on a piece you love. We’ll keep it here for you.
                </p>
                <Link className="button" href="/shop">
                  Find your favourites
                </Link>
              </div>
            )
          )}
          {state.unavailable.map((id, index) => (
            <div className="unavailable-saved" key={id}>
              <p>Saved piece {index + 1} is no longer available.</p>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => void toggle(id).catch(() => undefined)}
              >
                Remove unavailable piece
              </button>
            </div>
          ))}
        </>
      )}
    </>
  );
}

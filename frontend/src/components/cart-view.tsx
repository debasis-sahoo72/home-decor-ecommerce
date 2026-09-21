"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { money } from "@/lib/catalog";
import { request } from "@/lib/shopping-client";
type Item = {
  id: string;
  variant_id: string;
  name: string;
  slug: string;
  label: string;
  quantity: number;
  price: string;
  subtotal: string;
  available: boolean;
};
export default function CartView() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/v1/cart", { cache: "no-store", signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error("Your bag could not be loaded.");
        return r.json();
      })
      .then((data) => {
        setItems(data.items);
        setLoading(false);
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);
  async function remove(id: string) {
    setBusy(true);
    setError("");
    try {
      await request(`/cart/items/${id}`, undefined, "DELETE");
      setItems((current) => current.filter((i) => i.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      {loading && <p role="status">Loading your bag…</p>}
      <p role="alert" className="field-error">
        {error}
      </p>
      {!loading && !error && !items.length && (
        <div className="empty-note">
          Your bag is waiting for something lovely.{" "}
          <Link href="/shop">Explore the collection →</Link>
        </div>
      )}
      {items.map((i) => (
        <article className="bag-item" key={i.id}>
          <div>
            <h2>
              <Link href={`/product/${i.slug}`}>{i.name}</Link>
            </h2>
            <p>
              {i.label} · Quantity {i.quantity}
            </p>
            <p>
              {money(i.price)} each · {money(i.subtotal)}
            </p>
            {!i.available && (
              <p className="field-error">
                This quantity is no longer available. Remove it and choose
                another option.
              </p>
            )}
          </div>
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => remove(i.id)}
          >
            Remove {i.name}
          </button>
        </article>
      ))}
      {items.length > 0 && (
        <p className="muted">
          Items in your bag are not reserved. Checkout and payment will be
          available in a later release.
        </p>
      )}
    </>
  );
}

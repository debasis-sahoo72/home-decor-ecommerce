"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Product, money } from "@/lib/catalog";
import { request, Delivery, deliveryDate } from "@/lib/shopping-client";
import WishlistButton from "./wishlist-button";
export default function ProductPurchase({ product: p }: { product: Product }) {
  const [variantId, setVariantId] = useState(
    p.variants.find((v) => v.in_stock)?.id || p.variants[0]?.id || "",
  );
  const [quantity, setQuantity] = useState("1");
  const [pincode, setPincode] = useState("");
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [checking, setChecking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();
  const v = p.variants.find((v) => v.id === variantId);
  const qty = Number(quantity);
  const valid =
    !!v &&
    Number.isInteger(qty) &&
    qty >= 1 &&
    qty <= Math.min(100, v.available_stock);
  async function checkDelivery(event: React.FormEvent) {
    event.preventDefault();
    setChecking(true);
    setDelivery(null);
    setError("");
    const pin = pincode;
    try {
      const r = await fetch(`/api/v1/delivery/${pin}`, { cache: "no-store" });
      if (!r.ok)
        throw new Error("Delivery could not be checked. Please try again.");
      setDelivery(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delivery check failed.");
    } finally {
      setChecking(false);
    }
  }
  async function purchase(buyNow: boolean) {
    if (!valid || !v) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (buyNow) {
        if (!/^[0-9]{6}$/.test(pincode))
          throw new Error("Enter your PIN code before buying.");
        await request("/checkout/preview", {
          variant_id: v.id,
          quantity: qty,
          pincode,
        });
        await request("/cart/items", { variant_id: v.id, quantity: qty });
        router.push("/checkout");
      } else {
        await request("/cart/items", { variant_id: v.id, quantity: qty });
        setMessage("Added to your bag.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to continue.");
    } finally {
      setBusy(false);
    }
  }
  if (!v) return <p>There are no available options for this piece.</p>;
  const quote = delivery?.pincode === pincode ? delivery : null;
  return (
    <div className="purchase-panel">
      <div className="pdp-price" aria-live="polite">
        <strong>{money(v.price)}</strong>
        {v.compare_at_price && v.discount_percent > 0 && (
          <>
            <del>{money(v.compare_at_price)}</del>
            <span className="discount-label">Save {v.discount_percent}%</span>
          </>
        )}
      </div>
      <p className="stock-label">
        {v.in_stock ? "In stock" : "Currently out of stock"}
        <span>SKU: {v.sku}</span>
      </p>
      <fieldset className="variant-picker">
        <legend>Choose your option</legend>
        {p.variants.map((option) => (
          <label key={option.id}>
            <input
              type="radio"
              name="variant"
              value={option.id}
              checked={option.id === variantId}
              onChange={() => {
                setVariantId(option.id);
                setQuantity("1");
                setError("");
                setMessage("");
              }}
            />
            <span>
              {option.label}
              {!option.in_stock && " · Out of stock"}
            </span>
          </label>
        ))}
      </fieldset>
      <label className="quantity-label">
        Quantity
        <input
          className="input"
          type="number"
          min="1"
          max={Math.min(100, v.available_stock) || 1}
          step="1"
          value={quantity}
          disabled={!v.in_stock || busy}
          onChange={(e) => setQuantity(e.target.value)}
        />
      </label>
      {v.in_stock && !valid && (
        <p className="field-error">
          Choose between 1 and {Math.min(100, v.available_stock)} items.
        </p>
      )}
      <div className="purchase-buttons">
        <button
          className="button button-primary"
          disabled={busy || !valid}
          onClick={() => purchase(false)}
        >
          {busy ? "Please wait…" : "Add to bag"}
        </button>
        <WishlistButton id={p.id} name={p.name} />
      </div>
      <button
        className="button button-secondary buy-now"
        disabled={busy || !valid}
        onClick={() => purchase(true)}
      >
        Buy now
      </button>
      <p className="muted">
        Stock is checked when adding to your bag and again before ordering.
      </p>
      <div role="status">
        {message && (
          <p>
            {message}{" "}
            <Link className="text-link" href="/cart">
              View bag →
            </Link>
          </p>
        )}
      </div>
      <p role="alert" className="field-error">
        {error}
      </p>
      <form className="delivery-form" onSubmit={checkDelivery}>
        <label htmlFor="delivery-pin">Will it reach your home?</label>
        <p className="muted">
          Enter your PIN code to check availability and an estimated delivery
          window.
        </p>
        <div>
          <input
            id="delivery-pin"
            className="input"
            inputMode="numeric"
            pattern="[0-9]{6}"
            required
            maxLength={6}
            placeholder="6-digit PIN code"
            value={pincode}
            onChange={(e) => {
              setPincode(e.target.value.replace(/\D/g, ""));
              setDelivery(null);
            }}
          />
          <button className="button button-secondary" disabled={checking}>
            {checking ? "Checking…" : "Check"}
          </button>
        </div>
        <div role="status">
          {quote && (
            <p
              className={quote.serviceable ? "delivery-success" : "field-error"}
            >
              {quote.serviceable && quote.earliest && quote.latest && (
                <>
                  Estimated {deliveryDate(quote.earliest)}–
                  {deliveryDate(quote.latest)} · Delivery {money(quote.fee!)}
                  <br />
                </>
              )}
              {quote.message}
            </p>
          )}
        </div>
      </form>
    </div>
  );
}

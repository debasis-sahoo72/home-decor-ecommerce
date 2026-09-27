"use client";
import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { money } from "@/lib/catalog";
import { imageSource, isDemo, productName } from "@/lib/media";
import { request, Delivery, deliveryDate } from "@/lib/shopping-client";
type Item = {
  id: string;
  name: string;
  slug: string;
  label: string;
  sku: string;
  quantity: number;
  price: string;
  subtotal: string;
  available: boolean;
  available_stock: number;
  image: { url: string; alt: string } | null;
};
type Cart = {
  items: Item[];
  owner: string;
  item_count: number;
  subtotal: string;
  discount: string;
  merchandise_total: string;
  delivery_fee: string | null;
  total: string | null;
  delivery: Delivery | null;
  stock_valid: boolean;
};
export default function CartView() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pin, setPin] = useState("");
  const [checkedPin, setCheckedPin] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async (pincode = "") => {
    const response = await fetch(
      `/api/v1/cart${pincode ? `?pincode=${encodeURIComponent(pincode)}` : ""}`,
      { cache: "no-store" },
    );
    if (!response.ok)
      throw new Error("Your bag could not be refreshed. Please retry.");
    const data: Cart = await response.json();
    setCart(data);
  }, []);
  useEffect(() => {
    // This callback updates state only after the HTTP request completes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load().catch((e) => setError(e.message));
    const sync = () => {
      void load().catch((e) => {
        setCart(null);
        setError(e.message);
      });
    };
    window.addEventListener("focus", sync);
    return () => window.removeEventListener("focus", sync);
  }, [load]);
  async function change(path: string, body?: unknown, method = "DELETE") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(path, body, method);
      await load(checkedPin);
      setNotice("Your bag has been updated.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please retry.");
      await load(checkedPin).catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p className="field-error" role="alert">
        {error}{" "}
        {error && (
          <button
            className="text-button"
            onClick={() => {
              setError("");
              void load(checkedPin).catch((e) => setError(e.message));
            }}
          >
            Retry
          </button>
        )}
      </p>
      <p className="sr-only" role="status">
        {notice}
      </p>
      {!cart && !error && <p role="status">Preparing your bag…</p>}
      {cart && !cart.items.length && (
        <div className="empty-note">
          <p className="empty-symbol" aria-hidden="true">
            ◇
          </p>
          <h2>A little room for something lovely.</h2>
          <p>Discover thoughtful details to make your space feel like home.</p>
          <Link className="button" href="/shop">
            Explore the collection
          </Link>
        </div>
      )}
      {cart && cart.items.length > 0 && (
        <div className="cart-layout">
          <div>
            <div className="cart-list-heading">
              <h2>
                Your selection <span>({cart.item_count})</span>
              </h2>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => void change("/cart")}
              >
                Remove all
              </button>
            </div>
            {cart.items.map((i) => (
              <article className="cart-line" key={i.id}>
                <Link href={`/product/${i.slug}`} className="cart-photo">
                  {i.image ? (
                    <Image
                      src={imageSource(i.image.url)}
                      alt={i.image.alt}
                      fill
                      sizes="(max-width: 640px) 85px, 120px"
                    />
                  ) : (
                    <span>No image</span>
                  )}
                </Link>
                <div className="cart-line-info">
                  {isDemo(i.name) && (
                    <span className="inline-demo">Demo product</span>
                  )}
                  <h3>
                    <Link href={`/product/${i.slug}`}>
                      {productName(i.name)}
                    </Link>
                  </h3>
                  <p className="muted">{i.label}</p>
                  <p className="cart-unit-price">{money(i.price)} each</p>
                  <div className="cart-quantity">
                    <button
                      aria-label={`Decrease quantity of ${productName(i.name)}`}
                      disabled={
                        busy || i.quantity <= 1 || i.available_stock === 0
                      }
                      onClick={() =>
                        void change(
                          `/cart/items/${i.id}`,
                          {
                            quantity: Math.min(
                              i.quantity - 1,
                              i.available_stock,
                              100,
                            ),
                          },
                          "PATCH",
                        )
                      }
                    >
                      −
                    </button>
                    <span aria-label={`Quantity ${i.quantity}`}>
                      {i.quantity}
                    </span>
                    <button
                      aria-label={`Increase quantity of ${productName(i.name)}`}
                      disabled={
                        busy || i.quantity >= Math.min(100, i.available_stock)
                      }
                      onClick={() =>
                        void change(
                          `/cart/items/${i.id}`,
                          { quantity: i.quantity + 1 },
                          "PATCH",
                        )
                      }
                    >
                      +
                    </button>
                  </div>
                  {!i.available && (
                    <p className="field-error">
                      {i.available_stock
                        ? `Only ${i.available_stock} available. Reduce the quantity.`
                        : "This option is unavailable. Please remove it."}
                    </p>
                  )}
                </div>
                <div className="cart-line-end">
                  <strong>{money(i.subtotal)}</strong>
                  <button
                    className="text-button"
                    aria-label={`Remove ${productName(i.name)}`}
                    disabled={busy}
                    onClick={() => void change(`/cart/items/${i.id}`)}
                  >
                    Remove
                  </button>
                </div>
              </article>
            ))}
            <div className="cart-note">
              <span aria-hidden="true">◇</span>
              <p>
                {cart.owner === "account" ? (
                  "Your bag is saved to your account."
                ) : (
                  <>
                    Your bag is saved on this browser for 30 days.{" "}
                    <Link href="/login">Sign in</Link> to keep it across
                    devices.
                  </>
                )}
                <br />
                Items are not reserved until an order is confirmed.
              </p>
            </div>
            <Link className="text-link" href="/shop">
              ← Continue exploring
            </Link>
          </div>
          <aside className="cart-summary" aria-label="Order summary">
            <p className="eyebrow">Beautiful choices</p>
            <h2>Order summary</h2>
            <dl>
              <div>
                <dt>Subtotal</dt>
                <dd>{money(cart.subtotal)}</dd>
              </div>
              <div className="savings">
                <dt>Product savings</dt>
                <dd>−{money(cart.discount)}</dd>
              </div>
              <div>
                <dt>Items total</dt>
                <dd>{money(cart.merchandise_total)}</dd>
              </div>
              <div>
                <dt>Delivery</dt>
                <dd>
                  {cart.delivery_fee !== null
                    ? money(cart.delivery_fee)
                    : "Check PIN code"}
                </dd>
              </div>
            </dl>
            <form
              className="cart-delivery"
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError("");
                try {
                  await load(pin);
                  setCheckedPin(pin);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Please retry.");
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label htmlFor="cart-pin">Delivery to your door</label>
              <div>
                <input
                  id="cart-pin"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  placeholder="6-digit PIN code"
                  autoComplete="postal-code"
                />
                <button className="button" disabled={busy}>
                  Check
                </button>
              </div>
            </form>
            {cart.delivery && (
              <p
                className={
                  cart.delivery.serviceable ? "delivery-result" : "field-error"
                }
                role="status"
              >
                {cart.delivery.pincode}:{" "}
                {cart.delivery.serviceable &&
                cart.delivery.earliest &&
                cart.delivery.latest ? (
                  <>
                    Estimated {deliveryDate(cart.delivery.earliest)}–
                    {deliveryDate(cart.delivery.latest)}. Subject to stock and
                    confirmation.
                  </>
                ) : (
                  cart.delivery.message
                )}
              </p>
            )}
            <div className="cart-total">
              <span>
                {cart.total ? "Estimated total" : "Total before delivery"}
              </span>
              <strong>{money(cart.total || cart.merchandise_total)}</strong>
            </div>
            {!cart.stock_valid && (
              <p className="field-error">
                Review unavailable items before continuing.
              </p>
            )}
            {cart.stock_valid ? (
              <Link className="button button-warm" href="/checkout">
                Proceed to checkout
              </Link>
            ) : (
              <button className="button button-warm" disabled>
                Review unavailable items
              </button>
            )}
            <p id="checkout-note" className="muted cart-fine-print">
              Select your address at checkout. Prices, delivery and availability
              are checked again before payment.
            </p>
          </aside>
        </div>
      )}
    </>
  );
}

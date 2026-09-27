"use client";
import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AddressBook from "./address-book";
import { request, Delivery, deliveryDate } from "@/lib/shopping-client";
import { money } from "@/lib/catalog";
import { imageSource, productName, isDemo } from "@/lib/media";

type Address = {
  id: string;
  full_name: string;
  phone: string;
  line1: string;
  line2: string | null;
  city: string;
  state: string;
  pincode: string;
  is_default: boolean;
};
type Item = {
  id: string;
  name: string;
  quantity: number;
  price: string;
  image: { url: string; alt: string } | null;
};
type Quote = {
  quote_hash: string;
  address: Address;
  cart: {
    items: Item[];
    subtotal: string;
    discount: string;
    delivery_fee: string;
    total: string;
    delivery: Delivery;
  };
};
type Order = {
  id: string;
  number: string;
  status: string;
  subtotal: string;
  discount: string;
  delivery_fee: string;
  total: string;
  address: Address;
  delivery: Delivery;
  can_cancel: boolean;
  payment_started: boolean;
  items: { name: string; sku: string; quantity: number; price: string }[];
};
type PaymentOptions = {
  key: string;
  order_id: string;
  amount: number;
  currency: string;
};
type RazorpayConstructor = new (
  options: PaymentOptions & {
    name: string;
    handler: () => void;
    modal: { ondismiss: () => void };
    theme: { color: string };
  },
) => { open: () => void };
declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}

async function read<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { cache: "no-store" });
  if (!response.ok)
    throw new Error(
      response.status === 401
        ? "Please sign in to continue checkout."
        : "Could not load checkout. Please retry.",
    );
  return response.json();
}

async function paymentScript() {
  if (window.Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => {
      script.remove();
      reject(new Error("Payment window could not load. Please retry."));
    };
    document.body.appendChild(script);
  });
  if (!window.Razorpay)
    throw new Error("Payment window is unavailable. Please retry.");
}

export default function CheckoutView() {
  const router = useRouter();
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [selected, setSelected] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState(false);
  const key = useRef("");
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const auth = await fetch("/api/v1/auth/me", { cache: "no-store" });
        if (auth.status === 401) return;
        if (!auth.ok)
          throw new Error("Your account could not be checked. Please refresh.");
        const orderId = new URLSearchParams(window.location.search).get(
          "order",
        );
        const [rows, config, pending] = await Promise.all([
          read<Address[]>("/addresses"),
          read<{ payment_available: boolean }>("/checkout/config"),
          read<Order | null>(
            orderId
              ? `/checkout/orders/${encodeURIComponent(orderId)}`
              : "/checkout/pending",
          ),
        ]);
        if (active) {
          setSignedIn(true);
          setAddresses(rows);
          setSelected(rows.find((a) => a.is_default)?.id || rows[0]?.id || "");
          setAvailable(config.payment_available);
          setOrder(pending?.status === "cancelled" ? null : pending);
        }
      } catch (e) {
        if (active)
          setError(e instanceof Error ? e.message : "Please refresh.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please retry.");
    } finally {
      setBusy(false);
    }
  }
  async function checkPayment(id: string) {
    const result = await request<Order>(`/checkout/orders/${id}/confirm`);
    setOrder(result);
    if (result.status === "awaiting_payment")
      setNotice(
        "Payment has not been confirmed yet. Check again shortly; please do not pay twice.",
      );
  }
  async function pay() {
    await paymentScript();
    let current = order;
    if (!current && quote) {
      key.current ||= crypto.randomUUID();
      current = await request<Order>("/checkout/orders", {
        address_id: selected,
        quote_hash: quote.quote_hash,
        idempotency_key: key.current,
      });
      setOrder(current);
      window.history.replaceState(null, "", `/checkout?order=${current.id}`);
    }
    if (!current) return;
    const id = current.id;
    const options = await request<PaymentOptions>(
      `/checkout/orders/${id}/payment`,
    );
    setOrder({ ...current, can_cancel: false, payment_started: true });
    const popup = new window.Razorpay!({
      ...options,
      name: "Your Sanctuary",
      theme: { color: "#3f5138" },
      handler: () => {
        void action(() => checkPayment(id));
      },
      modal: {
        ondismiss: () => {
          setNotice(
            "Payment window closed. Your checkout is saved; check payment status before retrying.",
          );
        },
      },
    });
    popup.open();
  }
  if (loading) return <p role="status">Preparing your checkout…</p>;
  if (!signedIn)
    return (
      <div className="empty-note">
        <h2>Your bag, safely saved.</h2>
        <p>
          Sign in or create an account to select a delivery address and
          checkout. Your guest bag follows you when you sign in.
        </p>
        <p role="alert">{error}</p>
        <Link className="button button-primary" href="/login?next=checkout">
          Sign in to checkout
        </Link>
        <Link className="text-link" href="/cart">
          Return to your bag
        </Link>
      </div>
    );
  const paid = !!order && order.status !== "awaiting_payment";
  const summary = order || quote?.cart;
  return (
    <>
      <ol className="checkout-steps" aria-label="Checkout progress">
        {["Address", "Delivery & review", "Payment", "Confirmation"].map(
          (label, i) => (
            <li
              key={label}
              aria-current={
                i === (paid ? 3 : order ? 2 : quote ? 1 : 0)
                  ? "step"
                  : undefined
              }
            >
              <span>{i + 1}</span>
              {label}
            </li>
          ),
        )}
      </ol>
      <p className="field-error" role="alert">
        {error}
      </p>
      <p role="status">{notice}</p>
      {paid ? (
        <div className="checkout-confirmation">
          <p className="eyebrow">Thank you for making room for us</p>
          <h2>Your order is saved.</h2>
          <Link className="text-link" href={`/account/orders/${order.id}`}>
            View current order status
          </Link>
          <p>
            Order <strong>{order.number}</strong>
          </p>
          <p>Payment of {money(order.total)} verified.</p>
          <p>
            Standard delivery to {order.address.pincode}: estimated{" "}
            {deliveryDate(order.delivery.earliest!)}–
            {deliveryDate(order.delivery.latest!)}.
          </p>
          <Link className="button button-primary" href="/shop">
            Continue exploring
          </Link>
        </div>
      ) : null}
      <div className="checkout-grid">
        <div>
          {!order ? (
            <section className="checkout-panel">
              <h2>Where should it feel like home?</h2>
              <p className="muted">
                Select your shipping address. Delivery is checked by PIN code.
              </p>
              <fieldset className="checkout-addresses" disabled={busy}>
                <legend className="sr-only">Shipping address</legend>
                {addresses.map((a) => (
                  <label
                    key={a.id}
                    className={selected === a.id ? "selected" : ""}
                  >
                    <input
                      type="radio"
                      name="checkout-address"
                      checked={selected === a.id}
                      onChange={() => {
                        setSelected(a.id);
                        setQuote(null);
                        key.current = "";
                      }}
                    />
                    <span>
                      <strong>{a.full_name}</strong>
                      {a.is_default && <small> · Default</small>}
                      <br />
                      {a.line1}
                      {a.line2 && `, ${a.line2}`}
                      <br />
                      {a.city}, {a.state} – {a.pincode}
                      <br />
                      {a.phone}
                    </span>
                  </label>
                ))}
              </fieldset>
              {!addresses.length && (
                <p>No saved addresses yet. Add one to continue.</p>
              )}
              <button
                className="text-button"
                disabled={busy}
                onClick={() => {
                  setEditing(!editing);
                  setQuote(null);
                }}
              >
                Add or edit an address
              </button>
              {editing && (
                <div className="checkout-address-editor">
                  <AddressBook />
                  <button
                    className="button button-secondary"
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        const rows = await read<Address[]>("/addresses");
                        setAddresses(rows);
                        setSelected(
                          rows.find((a) => a.is_default)?.id ||
                            rows[0]?.id ||
                            "",
                        );
                        setEditing(false);
                        setQuote(null);
                      })
                    }
                  >
                    Use saved addresses
                  </button>
                </div>
              )}
              <button
                className="button button-primary"
                disabled={busy || !selected || editing}
                onClick={() =>
                  void action(async () => {
                    setQuote(null);
                    key.current = "";
                    setQuote(
                      await request<Quote>("/checkout/quote", {
                        address_id: selected,
                      }),
                    );
                  })
                }
              >
                {busy ? "Checking…" : "Check delivery & review order"}
              </button>
            </section>
          ) : (
            <section className="checkout-panel">
              <h2>{paid ? "Delivery address" : "Your checkout is saved"}</h2>
              <p>{order.number}</p>
              <address>
                {order.address.full_name}
                <br />
                {order.address.line1}
                <br />
                {order.address.city}, {order.address.state} –{" "}
                {order.address.pincode}
              </address>
              {!paid && (
                <p>
                  Stock is reserved for this checkout. Payment must be verified
                  before your order is confirmed.
                </p>
              )}
            </section>
          )}
          <Link className="text-link" href="/cart">
            ← Review your bag
          </Link>
        </div>
        <aside
          className="cart-summary checkout-summary"
          aria-label="Order summary"
        >
          <p className="eyebrow">Chosen for your sanctuary</p>
          <h2>Order summary</h2>
          {!summary ? (
            <p>
              Select an address to check stock, delivery and your final total.
            </p>
          ) : (
            <>
              <ul className="checkout-items">
                {summary.items.map((item, i) => (
                  <li key={i}>
                    {"image" in item && item.image && (
                      <Image
                        src={imageSource(item.image.url)}
                        alt={item.image.alt}
                        width={64}
                        height={80}
                      />
                    )}
                    <span>
                      {productName(item.name)}
                      {isDemo(item.name) && <small>Demo product</small>}
                      <small>
                        Quantity {item.quantity} · {money(item.price)} each
                      </small>
                    </span>
                  </li>
                ))}
              </ul>
              <dl>
                <div>
                  <dt>Subtotal</dt>
                  <dd>{money(summary.subtotal)}</dd>
                </div>
                <div>
                  <dt>Product savings</dt>
                  <dd>−{money(summary.discount)}</dd>
                </div>
                <div>
                  <dt>Standard delivery</dt>
                  <dd>{money(summary.delivery_fee)}</dd>
                </div>
              </dl>
              <p className="delivery-result">
                Estimated {deliveryDate(summary.delivery.earliest!)}–
                {deliveryDate(summary.delivery.latest!)}. Calendar days;
                confirmed after payment.
              </p>
              <div className="cart-total">
                <span>Total</span>
                <strong>{money(summary.total)}</strong>
              </div>
            </>
          )}
          {!paid && (
            <>
              {!available && (
                <p className="empty-note">
                  Online payment is not available yet. You can review your
                  delivery and total; your bag is saved.
                </p>
              )}
              {!available && !order && quote && (
                <button
                  className="button button-primary"
                  disabled={busy}
                  onClick={() =>
                    void action(async () => {
                      key.current ||= crypto.randomUUID();
                      const saved = await request<{ id: string }>("/orders", {
                        address_id: selected,
                        quote_hash: quote.quote_hash,
                        idempotency_key: key.current,
                      });
                      router.push(`/account/orders/${saved.id}`);
                    })
                  }
                >
                  Save order awaiting payment
                </button>
              )}
              {order && (
                <Link
                  className="text-link"
                  href={`/account/orders/${order.id}`}
                >
                  View order details
                </Link>
              )}
              <button
                className="button button-warm"
                disabled={busy || !available || (!quote && !order)}
                onClick={() => void action(pay)}
              >
                {busy
                  ? "Please wait…"
                  : order
                    ? "Resume secure payment"
                    : "Continue to secure payment"}
              </button>
              {order && (
                <button
                  className="button button-secondary"
                  disabled={busy}
                  onClick={() => void action(() => checkPayment(order.id))}
                >
                  Check payment status
                </button>
              )}
              {order?.can_cancel && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() =>
                    void action(async () => {
                      await request(`/checkout/orders/${order.id}/cancel`);
                      setOrder(null);
                      setQuote(null);
                      key.current = "";
                      window.history.replaceState(null, "", "/checkout");
                    })
                  }
                >
                  Cancel checkout & return to review
                </button>
              )}
              <p className="cart-fine-print muted">
                Prices and availability are checked again before payment.
                Confirmation appears only after payment is verified.
              </p>
            </>
          )}
        </aside>
      </div>
    </>
  );
}

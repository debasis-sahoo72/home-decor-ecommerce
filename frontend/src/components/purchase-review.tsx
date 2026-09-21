"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { request, Purchase, deliveryDate } from "@/lib/shopping-client";
import { money } from "@/lib/catalog";
export default function PurchaseReview({
  variantId,
  quantity,
  pincode,
}: {
  variantId: string;
  quantity: number;
  pincode: string;
}) {
  const [result, setResult] = useState<Purchase | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    request<Purchase>("/checkout/preview", {
      variant_id: variantId,
      quantity,
      pincode,
    })
      .then((data) => {
        if (current) setResult(data);
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [variantId, quantity, pincode]);
  if (error)
    return (
      <div role="alert" className="empty-note">
        <p>{error}</p>
        <Link href="/shop">Return to the shop</Link>
      </div>
    );
  if (!result) return <p role="status">Checking current stock and delivery…</p>;
  return (
    <div className="purchase-review">
      <h2>{result.name}</h2>
      <p>
        {result.label} · Quantity {result.quantity}
      </p>
      <p>
        Item subtotal: <strong>{money(result.subtotal)}</strong>
      </p>
      <p>
        Delivery to {pincode}: {money(result.delivery.fee!)}
      </p>
      <p>
        Estimated delivery: {deliveryDate(result.delivery.earliest!)}–
        {deliveryDate(result.delivery.latest!)}
      </p>
      <p className="muted">
        Final charges will be confirmed when checkout opens.
      </p>
      <div className="empty-note">
        <h3>Payment is not available yet.</h3>
        <p>{result.message}</p>
        <Link href="/cart">View your bag →</Link>
        <Link href="/shop">Continue exploring →</Link>
      </div>
    </div>
  );
}

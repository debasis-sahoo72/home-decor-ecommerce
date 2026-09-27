"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { request } from "@/lib/shopping-client";

type Review = { id: string; status: string; rating: number; body: string };
type Eligibility = { eligible: boolean; review: Review | null };

export default function ProductReviewForm({ productId }: { productId: string }) {
  const [state, setState] = useState<Eligibility | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/v1/products/${productId}/review-eligibility`, {
      cache: "no-store", signal: controller.signal,
    }).then(async (response) => {
      if (response.status === 401) return null;
      if (!response.ok) throw new Error("Review eligibility could not be loaded.");
      return response.json() as Promise<Eligibility>;
    }).then((data) => { if (!controller.signal.aborted) setState(data); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [productId, retry]);

  if (loading) return <p role="status">Checking review eligibility…</p>;
  if (!state) return error ? <p role="alert">{error} <button onClick={() => {
    setError(""); setLoading(true); setRetry(retry + 1);
  }}>Retry</button></p> : <p><Link href="/login">Sign in</Link> to review a product you have received.</p>;
  if (state.review) return <div className="review-card" role="status">
    <h3>Your review</h3>
    <p>{state.review.rating} out of 5 · {state.review.status === "pending" ? "Awaiting moderation" : state.review.status === "published" ? "Published" : "Not approved for publication"}</p>
    <p className="preserve-text">{state.review.body}</p>
  </div>;
  if (!state.eligible) return <p className="muted">Reviews are available to customers after this product is delivered. One review per customer per product.</p>;
  return <form className="review-card review-form" onSubmit={async (event) => {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const review = await request<Review>(`/products/${productId}/reviews`, {
        rating: Number(data.get("rating")), body: String(data.get("body")).trim(),
      });
      setState({ eligible: false, review });
    } catch (e) { setError(e instanceof Error ? e.message : "Please try again."); }
    finally { setBusy(false); }
  }}>
    <h3>Share your experience</h3>
    <p>Your review will appear after moderation. Please leave out personal information.</p>
    <label htmlFor="review-rating">Rating</label>
    <select id="review-rating" name="rating" required defaultValue="">
      <option value="" disabled>Choose a rating</option>
      {[5, 4, 3, 2, 1].map((n) => <option value={n} key={n}>{n} out of 5</option>)}
    </select>
    <label htmlFor="review-body">Your review</label>
    <textarea id="review-body" name="body" required minLength={10} maxLength={2000} rows={5} />
    <p className="muted">10–2,000 characters. One review per customer per product.</p>
    {error && <p role="alert">{error}</p>}
    <button className="button" disabled={busy}>{busy ? "Submitting…" : "Submit review"}</button>
  </form>;
}

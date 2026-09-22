"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

export default function CatalogUnavailable() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <section className="wrap section" aria-labelledby="catalog-unavailable">
      <p className="eyebrow">A little pause</p>
      <h1 id="catalog-unavailable">The collection is temporarily unavailable.</h1>
      <p>We could not load the products. Please try again in a moment.</p>
      <button className="button button-primary" disabled={pending}
        onClick={() => startTransition(() => router.refresh())}>
        {pending ? "Checking the collection…" : "Try again"}
      </button>
      <p role="status" className="sr-only">{pending ? "Loading the collection" : ""}</p>
    </section>
  );
}

"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { readApi } from "@/lib/orders";
export const sections = [
  "dashboard",
  "products",
  "categories",
  "inventory",
  "orders",
  "customers",
  "delivery",
  "reviews",
];
export default function AdminShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = useState("loading");
  const path = usePathname();
  useEffect(() => {
    const c = new AbortController();
    readApi<{ role: string }>("/auth/me", c.signal)
      .then((u) => setState(u.role === "admin" ? "admin" : "denied"))
      .catch(() => {
        if (!c.signal.aborted) setState("denied");
      });
    return () => c.abort();
  }, []);
  if (state === "loading")
    return (
      <section className="wrap section" role="status">
        Checking administrator access…
      </section>
    );
  if (state !== "admin")
    return (
      <section className="wrap section">
        <h1>Administrator access required</h1>
        <p>Sign in with your administrator account to manage the store.</p>
        <Link className="button button-primary" href="/login?next=admin">
          Sign in
        </Link>
      </section>
    );
  return (
    <div className="wrap ops-layout">
      <nav className="ops-nav" aria-label="Administration">
        <h2>Store management</h2>
        {sections.map((s) => {
          const url = s === "dashboard" ? "/admin" : `/admin/${s}`;
          return (
            <Link
              key={s}
              href={url}
              aria-current={
                path === url ||
                (s !== "dashboard" && path.startsWith(url + "/"))
                  ? "page"
                  : undefined
              }
            >
              {s === "delivery"
                ? "Delivery PIN codes"
                : s[0].toUpperCase() + s.slice(1)}
            </Link>
          );
        })}
      </nav>
      <div>{children}</div>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useShopping } from "./shopping-provider";
import { request } from "@/lib/shopping-client";
export default function SignIn() {
  const router = useRouter();
  const { refresh } = useShopping();
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    fetch("/api/v1/auth/me", { cache: "no-store" })
      .then(async (r) => {
        if (r.ok) setUser(await r.json());
        else if (r.status !== 401)
          throw new Error("Could not check your account. Refresh to retry.");
      })
      .catch((e) => setMessage(e.message))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <p role="status">Checking your account…</p>;
  return (
    <div className="account-panel">
      <p className="eyebrow">Make yourself at home</p>
      <h1>
        {user
          ? `Hello, ${user.name}`
          : register
            ? "Join our little world."
            : "Welcome back."}
      </h1>
      {user ? (
        <>
          <p>Your bag and wishlist stay with your account across devices.</p>
          <div className="account-links">
            <Link className="button button-secondary" href="/account/orders">
              Your orders
            </Link>
            {user.role === "admin" && (
              <Link className="button button-secondary" href="/admin">
                Admin dashboard
              </Link>
            )}
            <Link className="button button-secondary" href="/account/addresses">
              Your addresses
            </Link>
            <Link className="button button-primary" href="/cart">
              Your bag
            </Link>
            <Link className="button button-secondary" href="/wishlist">
              Your wishlist
            </Link>
          </div>
          <button
            className="text-button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await request("/auth/logout");
                setUser(null);
                await refresh();
                setBusy(false);
                router.refresh();
              } catch (e) {
                setMessage(e instanceof Error ? e.message : "Please retry.");
                setBusy(false);
              }
            }}
          >
            Sign out
          </button>
        </>
      ) : (
        <>
          <p className="muted">
            Keep your favourite pieces and your bag together, wherever you
            browse.
          </p>
          <form
            className="account-form"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setMessage("");
              const data = new FormData(e.currentTarget);
              const email = data.get("email"),
                password = data.get("password");
              try {
                if (register)
                  await request("/auth/register", {
                    email,
                    password,
                    name: data.get("name"),
                  });
                await request("/auth/login", { email, password });
                await refresh();
                router.push(
                  new URLSearchParams(window.location.search).get("next") ===
                    "orders"
                    ? "/account/orders"
                    : new URLSearchParams(window.location.search).get(
                          "next",
                        ) === "admin"
                      ? "/admin"
                      : new URLSearchParams(window.location.search).get(
                            "next",
                          ) === "addresses"
                        ? "/account/addresses"
                        : new URLSearchParams(window.location.search).get(
                              "next",
                            ) === "checkout"
                          ? "/checkout"
                          : "/cart",
                );
                router.refresh();
              } catch (e) {
                setMessage(e instanceof Error ? e.message : "Please retry.");
                setBusy(false);
              }
            }}
          >
            {register && (
              <label>
                Your name
                <input
                  name="name"
                  autoComplete="name"
                  required
                  minLength={2}
                  maxLength={100}
                />
              </label>
            )}
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                maxLength={254}
                required
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={register ? 15 : 1}
                maxLength={128}
                aria-describedby={register ? "password-help" : undefined}
              />
            </label>
            {register && (
              <p id="password-help" className="muted">
                Use a passphrase of 15–128 characters with at least 5 different
                characters.
              </p>
            )}
            <button className="button button-primary" disabled={busy}>
              {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
            </button>
          </form>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              setRegister(!register);
              setMessage("");
            }}
          >
            {register
              ? "Already have an account? Sign in"
              : "New here? Create an account"}
          </button>
          <p className="cart-fine-print muted">
            Your guest bag joins your account when you sign in. Quantities may
            be adjusted to available stock; please review your bag.
          </p>
        </>
      )}
      <p role="alert" className="field-error">
        {message}
      </p>
    </div>
  );
}

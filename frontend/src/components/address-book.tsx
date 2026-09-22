"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { request } from "@/lib/shopping-client";
type Address = {
  id: string;
  full_name: string;
  phone: string;
  line1: string;
  line2: string | null;
  landmark: string | null;
  city: string;
  state: string;
  country: string;
  pincode: string;
  is_default: boolean;
};
const fields = [
  { key: "full_name", label: "Full name", auto: "name", max: 100, min: 2 },
  { key: "phone", label: "Mobile number", auto: "tel", max: 20, min: 10 },
  {
    key: "line1",
    label: "Address line 1",
    auto: "address-line1",
    max: 200,
    min: 5,
  },
  {
    key: "line2",
    label: "Address line 2 (optional)",
    auto: "address-line2",
    max: 200,
  },
  { key: "landmark", label: "Landmark (optional)", auto: "off", max: 200 },
  { key: "city", label: "City", auto: "address-level2", max: 100, min: 2 },
  {
    key: "state",
    label: "State / Union territory",
    auto: "address-level1",
    max: 100,
    min: 2,
  },
  { key: "pincode", label: "PIN code", auto: "postal-code", max: 6, min: 6 },
] as const;
async function readAddresses(): Promise<Address[] | null> {
  const response = await fetch("/api/v1/addresses", { cache: "no-store" });
  if (response.status === 401) return null;
  if (!response.ok)
    throw new Error("We couldn’t load your addresses. Please retry.");
  return response.json();
}
export default function AddressBook() {
  const [addresses, setAddresses] = useState<Address[] | null>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Address | "new" | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    let active = true;
    const sync = () => {
      void readAddresses()
        .then((data) => {
          if (active) {
            setAddresses(data);
            setEditing((current) =>
              data === null ||
              (current &&
                current !== "new" &&
                !data.some((a) => a.id === current.id))
                ? null
                : current,
            );
            setError("");
          }
        })
        .catch((e) => {
          if (active) {
            setAddresses([]);
            setError(e.message);
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    };
    sync();
    window.addEventListener("focus", sync);
    return () => {
      active = false;
      window.removeEventListener("focus", sync);
    };
  }, []);
  useEffect(() => {
    if (editing)
      formRef.current?.querySelector<HTMLInputElement>("input")?.focus();
  }, [editing]);
  async function mutate(
    path: string,
    body: unknown,
    method: string,
    message: string,
  ) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(path, body, method);
      setEditing(null);
      setRemoving(null);
      setAddresses(await readAddresses());
      setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please retry.");
    } finally {
      setBusy(false);
    }
  }
  const draft = editing && editing !== "new" ? editing : null;
  return (
    <>
      <nav className="account-nav" aria-label="Account navigation">
        <Link href="/login">Account</Link>
        <Link href="/account/addresses" aria-current="page">
          Addresses
        </Link>
        <Link href="/wishlist">Wishlist</Link>
        <Link href="/cart">Shopping bag</Link>
      </nav>
      <p className="field-error" role="alert">
        {error}{" "}
        {error && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              void readAddresses()
                .then((data) => {
                  setAddresses(data);
                  setError("");
                })
                .catch((e) => setError(e.message));
            }}
          >
            Retry loading
          </button>
        )}
      </p>
      <p role="status" className="address-notice">
        {notice}
      </p>
      {loading ? (
        <p role="status">Loading your addresses…</p>
      ) : addresses === null ? (
        <div className="empty-note">
          <h2>Your places, kept private.</h2>
          <p>Sign in to manage your delivery addresses.</p>
          <Link className="button button-primary" href="/login?next=addresses">
            Sign in to your account
          </Link>
        </div>
      ) : (
        <>
          <div className="address-heading">
            <p className="muted">
              Save the details once, for easier checkout later.
            </p>
            <button
              className="button button-primary"
              disabled={busy || addresses.length >= 20}
              onClick={() => {
                setEditing("new");
                setError("");
                setNotice("");
              }}
            >
              + Add address
            </button>
          </div>
          {editing && (
            <form
              ref={formRef}
              key={draft?.id || "new"}
              className="address-form"
              onSubmit={(e) => {
                e.preventDefault();
                const data = new FormData(e.currentTarget);
                const body = Object.fromEntries(
                  fields.map((field) => [
                    field.key,
                    String(data.get(field.key) || "").trim() || null,
                  ]),
                );
                void mutate(
                  draft ? `/addresses/${draft.id}` : "/addresses",
                  {
                    ...body,
                    country: "IN",
                    is_default:
                      draft?.is_default || data.get("is_default") === "on",
                  },
                  draft ? "PUT" : "POST",
                  draft ? "Address updated." : "Address saved.",
                );
              }}
            >
              <h2>{draft ? "Edit address" : "A new place to deliver"}</h2>
              <p className="muted">
                India delivery addresses only. Saving an address does not
                confirm serviceability.
              </p>
              <fieldset disabled={busy}>
                <legend className="sr-only">Address details</legend>
                <div className="address-fields">
                  {fields.map((field) => (
                    <label key={field.key} htmlFor={`address-${field.key}`}>
                      {field.label}
                      <input
                        id={`address-${field.key}`}
                        name={field.key}
                        defaultValue={draft?.[field.key] || ""}
                        required={"min" in field}
                        minLength={"min" in field ? field.min : undefined}
                        maxLength={field.max}
                        autoComplete={field.auto}
                        type={field.key === "phone" ? "tel" : "text"}
                        inputMode={
                          field.key === "pincode" ? "numeric" : undefined
                        }
                        pattern={
                          field.key === "pincode"
                            ? "[1-9][0-9]{5}"
                            : field.key === "phone"
                              ? "(?:\\+91[ ()-]*)?[6-9](?:[ ()-]*[0-9]){9}"
                              : undefined
                        }
                        aria-describedby={
                          field.key === "phone"
                            ? "address-phone-help"
                            : undefined
                        }
                      />
                      {field.key === "phone" && (
                        <small id="address-phone-help">
                          10-digit Indian mobile number; +91 is optional.
                        </small>
                      )}
                    </label>
                  ))}
                  <label htmlFor="address-country">
                    Country
                    <select
                      id="address-country"
                      name="country"
                      autoComplete="country"
                      defaultValue="IN"
                    >
                      <option value="IN">India</option>
                    </select>
                  </label>
                </div>
                <label className="address-default">
                  <input
                    type="checkbox"
                    name="is_default"
                    defaultChecked={draft?.is_default || addresses.length === 0}
                    disabled={draft?.is_default || addresses.length === 0}
                  />
                  {draft?.is_default
                    ? "This is your default address"
                    : addresses.length === 0
                      ? "Your first address will be the default"
                      : "Make this my default address"}
                </label>
                <div className="account-links">
                  <button className="button button-primary" type="submit">
                    {busy ? "Saving…" : "Save address"}
                  </button>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => setEditing(null)}
                  >
                    Cancel
                  </button>
                </div>
              </fieldset>
            </form>
          )}
          {!addresses.length && !editing && !error && (
            <div className="empty-note">
              <h2>Where should lovely things arrive?</h2>
              <p>Add your first delivery address to get started.</p>
            </div>
          )}
          <div className="address-grid">
            {addresses.map((address) => (
              <article
                className={`address-card ${address.is_default ? "address-card-default" : ""}`}
                key={address.id}
              >
                <div className="address-card-top">
                  <h2>{address.full_name}</h2>
                  {address.is_default && (
                    <span className="address-badge">Default</span>
                  )}
                </div>
                <address>
                  <p>
                    {address.line1}
                    <br />
                    {address.line2 && (
                      <>
                        {address.line2}
                        <br />
                      </>
                    )}
                    {address.landmark && (
                      <>
                        Near {address.landmark}
                        <br />
                      </>
                    )}
                    {address.city}, {address.state} – {address.pincode}
                    <br />
                    India
                  </p>
                  <p>{address.phone}</p>
                </address>
                <div className="address-actions">
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => {
                      setEditing(address);
                      setError("");
                    }}
                  >
                    Edit
                  </button>
                  {!address.is_default && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        void mutate(
                          `/addresses/${address.id}/default`,
                          undefined,
                          "POST",
                          "Default address updated.",
                        )
                      }
                    >
                      Set as default
                    </button>
                  )}
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => setRemoving(address.id)}
                  >
                    Delete
                  </button>
                </div>
                {removing === address.id && (
                  <div
                    className="address-delete"
                    role="group"
                    aria-label="Confirm address deletion"
                  >
                    <p>
                      Delete this saved address?
                      {address.is_default && addresses.length > 1
                        ? " Another address will become your default."
                        : ""}
                    </p>
                    <button
                      className="button button-secondary"
                      disabled={busy}
                      onClick={() =>
                        void mutate(
                          `/addresses/${address.id}`,
                          undefined,
                          "DELETE",
                          "Address deleted.",
                        )
                      }
                    >
                      Yes, delete
                    </button>{" "}
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => setRemoving(null)}
                    >
                      Keep address
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </>
  );
}

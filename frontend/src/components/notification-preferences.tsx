"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { request } from "@/lib/shopping-client";

type Preferences = { whatsapp_enabled: boolean; whatsapp_phone: string | null; whatsapp_available: boolean };

export default function NotificationPreferences() {
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/v1/account/notifications", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (response.status === 401) return null;
        if (!response.ok) throw new Error("Preferences could not be loaded. Please refresh to retry.");
        return response.json() as Promise<Preferences>;
      }).then((data) => { if (!controller.signal.aborted) { setPreferences(data); setEnabled(data?.whatsapp_enabled ?? false); } })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  if (loading) return <p role="status">Loading preferences…</p>;
  if (!preferences) return error ? <p role="alert">{error}</p> : <p><Link className="text-link" href="/login">Sign in</Link> to manage your notifications.</p>;
  return <form className="review-card review-form" onSubmit={async (event) => {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError(""); setSaved(false);
    try {
      const next = await request<Preferences>("/account/notifications", {
        whatsapp_enabled: enabled,
        whatsapp_phone: enabled ? String(data.get("phone")).trim() : null,
      }, "PUT");
      setPreferences(next); setSaved(true);
    } catch (e) { setError(e instanceof Error ? e.message : "Please try again."); }
    finally { setBusy(false); }
  }}>
    <h2>Order updates</h2>
    <p>Transactional email updates use your account email. WhatsApp updates are optional and contain only a brief status and order reference.</p>
    {!preferences.whatsapp_available && <p className="muted">WhatsApp sending is not active yet. You can save your preference for future order updates.</p>}
    <label className="checkbox-label">
      <input type="checkbox" checked={enabled} onChange={(e) => { setEnabled(e.target.checked); setSaved(false); }} />
      I agree to receive transactional WhatsApp updates from Your Sanctuary at my number below. I can turn these off here at any time.
    </label>
    <label htmlFor="notification-phone">Your WhatsApp number, including country code</label>
    <input className="input" style={{ padding: "12px", borderWidth: 1, width: "100%" }} id="notification-phone" name="phone" type="tel" autoComplete="tel" placeholder="+919876543210" pattern="\+[1-9][0-9]{7,14}" maxLength={16} required={enabled} disabled={!enabled} defaultValue={preferences.whatsapp_phone || ""} />
    <p className="muted">Use your own number. No marketing messages. Turning off WhatsApp does not affect essential account or order emails.</p>
    {error && <p role="alert">{error}</p>}
    {saved && <p role="status">Your preferences have been saved.</p>}
    <button className="button" disabled={busy}>{busy ? "Saving…" : "Save preferences"}</button>
  </form>;
}

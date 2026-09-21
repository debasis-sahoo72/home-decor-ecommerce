"use client";
import { useSyncExternalStore, useState } from "react";
const key = "decor-wishlist-v1";
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("wishlist-change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("wishlist-change", callback);
  };
}
function snapshot() {
  try {
    return localStorage.getItem(key) || "[]";
  } catch {
    return "[]";
  }
}
export function useSaved() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => "[]");
  try {
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value)
      ? value
          .filter(
            (id): id is string =>
              typeof id === "string" && /^[0-9a-f-]{36}$/.test(id),
          )
          .slice(0, 200)
      : [];
  } catch {
    return [];
  }
}
export default function WishlistButton({
  id,
  name,
}: {
  id: string;
  name: string;
}) {
  const ids = useSaved();
  const saved = ids.includes(id);
  const [message, setMessage] = useState("");
  function toggle() {
    try {
      const next = saved
        ? ids.filter((v) => v !== id)
        : [...ids, id].slice(-200);
      localStorage.setItem(key, JSON.stringify(next));
      window.dispatchEvent(new Event("wishlist-change"));
      setMessage(saved ? "Removed from saved pieces" : "Saved on this device");
    } catch {
      setMessage("Your browser could not save this piece.");
    }
  }
  return (
    <>
      <button
        className="wishlist-button"
        type="button"
        aria-pressed={saved}
        aria-label={`${saved ? "Unsave" : "Save"} ${name}`}
        onClick={toggle}
      >
        {saved ? "♥" : "♡"}
      </button>
      <span role="status" className="sr-only">
        {message}
      </span>
    </>
  );
}

"use client";
import { useState } from "react";
import { useShopping } from "./shopping-provider";
export function useSaved() {
  return useShopping().ids;
}
export default function WishlistButton({
  id,
  name,
}: {
  id: string;
  name: string;
}) {
  const { ids, toggle, ready, busy } = useShopping();
  const saved = ids.includes(id);
  const [message, setMessage] = useState("");
  return (
    <>
      <button
        className="wishlist-button"
        type="button"
        aria-pressed={saved}
        aria-label={`${saved ? "Unsave" : "Save"} ${name}`}
        disabled={!ready || busy}
        onClick={async () => {
          try {
            await toggle(id);
            setMessage(saved ? "Removed from wishlist" : "Saved to wishlist");
          } catch (e) {
            setMessage(e instanceof Error ? e.message : "Please retry.");
          }
        }}
      >
        {saved ? "♥" : "♡"}
      </button>
      <span role="status" className="sr-only">
        {message}
      </span>
    </>
  );
}

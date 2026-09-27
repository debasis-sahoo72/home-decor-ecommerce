"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from "react";
import { request } from "@/lib/shopping-client";
const key = "decor-wishlist-v1";
type State = {
  ids: string[];
  account: boolean;
  ready: boolean;
  error: string;
  busy: boolean;
  toggle: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
};
const Context = createContext<State | null>(null);
function guestIds(): string[] {
  const value: unknown = JSON.parse(localStorage.getItem(key) || "[]");
  return Array.isArray(value)
    ? [
        ...new Set(
          value.filter(
            (id): id is string =>
              typeof id === "string" && /^[0-9a-f-]{36}$/i.test(id),
          ),
        ),
      ].slice(0, 200)
    : [];
}
export function ShoppingProvider({ children }: { children: React.ReactNode }) {
  const [ids, setIds] = useState<string[]>([]);
  const [account, setAccount] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const working = useRef(false);
  const refresh = useCallback(async () => {
    if (working.current) return;
    working.current = true;

    try {
      const me = await fetch("/api/v1/auth/me", { cache: "no-store" });
      if (me.status !== 401 && !me.ok)
        throw new Error("Your saved pieces could not be loaded. Please retry.");
      const signedIn = me.ok;
      setAccount(signedIn);
      if (signedIn) {
        let guest: string[] = [];
        try {
          guest = guestIds();
        } catch {
          /* Device storage may be disabled. */
        }
        const response = guest.length
          ? await request<{ product_ids: string[] }>("/wishlist/merge", {
              product_ids: guest,
            })
          : await fetch("/api/v1/wishlist", { cache: "no-store" }).then(
              async (r) => {
                if (!r.ok)
                  throw new Error("Your saved pieces could not be loaded.");
                return r.json();
              },
            );
        setIds(response.product_ids);
        if (guest.length) localStorage.removeItem(key);
      } else {
        setIds(guestIds());
      }
      setError("");
      setReady(true);
    } catch (e) {
      setReady(false);
      setError(
        e instanceof Error ? e.message : "Saved pieces are unavailable.",
      );
    } finally {
      working.current = false;
    }
  }, []);
  useEffect(() => {
    // State updates happen after fetching the current identity, not during the effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
    const sync = () => {
      void refresh();
    };
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, [refresh]);
  async function toggle(id: string) {
    if (working.current || !ready) return;
    working.current = true;
    setBusy(true);
    try {
      const saved = ids.includes(id);
      if (account) {
        await request(
          saved ? `/wishlist/items/${id}` : "/wishlist/items",
          saved ? undefined : { product_id: id },
          saved ? "DELETE" : "POST",
        );
      } else {
        const current = guestIds();
        if (!current.includes(id) && current.length >= 200)
          throw new Error("Your wishlist can hold up to 200 pieces.");
        localStorage.setItem(
          key,
          JSON.stringify(
            saved
              ? current.filter((v) => v !== id)
              : [...new Set([...current, id])],
          ),
        );
      }
      setIds(saved ? ids.filter((v) => v !== id) : [...new Set([...ids, id])]);
      window.dispatchEvent(new Event("shopping:changed"));
      setError("");
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "Could not save this piece.";
      setError(message);
      throw new Error(message);
    } finally {
      working.current = false;
      setBusy(false);
    }
  }
  return (
    <Context.Provider
      value={{ ids, account, ready, error, busy, toggle, refresh }}
    >
      {children}
    </Context.Provider>
  );
}
export function useShopping() {
  const state = useContext(Context);
  if (!state) throw new Error("Shopping provider missing");
  return state;
}

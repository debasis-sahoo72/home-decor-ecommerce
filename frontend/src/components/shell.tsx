"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import Icon from "./icon";
import Brand from "./brand";
import { useShopping } from "./shopping-provider";
export function Header() {
  const { ids } = useShopping();
  const [cartCount, setCartCount] = useState(0);
  const refreshCart = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/cart", { cache: "no-store" });
      if (response.ok) setCartCount((await response.json()).item_count || 0);
    } catch { /* Header counts are progressive enhancement. */ }
  }, []);
  useEffect(() => {
    // Header state is synchronized with the external cart API after mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshCart();
    const update = () => void refreshCart();
    window.addEventListener("shopping:changed", update);
    window.addEventListener("focus", update);
    return () => {
      window.removeEventListener("shopping:changed", update);
      window.removeEventListener("focus", update);
    };
  }, [refreshCart]);
  return (
    <>
      <div className="announcement">
        Beautiful spaces. Happier living.{" "}
        <span>Delivery availability checked by PIN code.</span>
      </div>
      <header className="store-header">
        <div className="site-header wrap">
          <Brand />
          <form action="/shop" role="search" className="header-search">
            <label className="sr-only" htmlFor="header-search">
              Search home decor
            </label>
            <input
              id="header-search"
              name="q"
              type="search"
              maxLength={100}
              placeholder="Search for vases, lighting, textiles…"
            />
            <button type="submit" aria-label="Search">
              <Icon name="search" />
            </button>
          </form>
          <div className="header-actions">
            <Link href="/login" aria-label="Your account">
              <Icon name="user" />
              <span>Account</span>
            </Link>
            <Link href="/wishlist" aria-label={`Saved pieces${ids.length ? `, ${ids.length} item${ids.length === 1 ? "" : "s"}` : ""}`} className="header-count-link">
              <Icon name="heart" />
              <span>Wishlist</span>
              {ids.length > 0 && <b className="header-count" aria-label={`${ids.length} saved`}>{ids.length}</b>}
            </Link>
            <Link href="/cart" aria-label={`Shopping bag${cartCount ? `, ${cartCount} item${cartCount === 1 ? "" : "s"}` : ""}`} className="header-count-link">
              <Icon name="bag" />
              <span>Bag</span>
              {cartCount > 0 && <b className="header-count" aria-label={`${cartCount} in bag`}>{cartCount}</b>}
            </Link>
          </div>
        </div>
        <nav className="store-nav wrap" aria-label="Main navigation">
          <Link href="/">Home</Link>
          <Link href="/shop">Shop all</Link>
          <Link href="/categories/decor-objects">Decor objects</Link>
          <Link href="/categories/textiles">Soft furnishings</Link>
          <Link href="/categories/lighting">Lighting</Link>
          <Link href="/shop?sort=newest">New arrivals</Link>
          <Link className="offers-link" href="/shop?on_sale=true">
            Offers
          </Link>
        </nav>
      </header>
    </>
  );
}
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="wrap footer-grid">
        <div>
          <Brand footer />
          <h3>A little more you. In every room.</h3>
          <p>
            Warm textures, sculptural details and everyday inspiration for a
            home that tells your story.
          </p>
        </div>
        <nav aria-label="Footer navigation">
          <p className="eyebrow">Explore</p>
          <Link href="/shop">All pieces</Link>
          <Link href="/shop?sort=newest">New arrivals</Link>
          <Link href="/shop?on_sale=true">Offers</Link>
          <Link href="/wishlist">Your wishlist</Link>
        </nav>
        <div>
          <p className="eyebrow">Make yourself at home</p>
          <p>Based in Bangalore, India.</p>
          <p>Check your PIN code on each product for delivery availability.</p>
          <p className="footer-demo">
            Products marked Demo are preview samples with illustrative imagery
            and prices.
          </p>
        </div>
      </div>
      <div className="wrap footer-bottom">
        <span>© {new Date().getFullYear()} Your Sanctuary</span>
        <span>Considered details. Everyday beauty.</span>
      </div>
    </footer>
  );
}

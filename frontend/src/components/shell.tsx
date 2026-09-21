import Link from "next/link";
export function Header() {
  return (
    <>
      <div className="announcement">
        Thoughtful details. A home that feels like you.
      </div>
      <header className="site-header wrap">
        <Link className="wordmark" href="/" aria-label="Home Decor home">
          home<span>decor.</span>
        </Link>
        <nav aria-label="Main navigation">
          <Link href="/shop">Shop all</Link>
          <Link href="/shop?sort=newest">New arrivals</Link>
          <Link href="/shop?featured=true">The edit</Link>
        </nav>
        <Link className="saved-link" href="/wishlist">
          ♡ <span>Saved pieces</span>
        </Link>
        <Link className="saved-link" href="/cart">
          Bag
        </Link>
      </header>
    </>
  );
}
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="wrap footer-grid">
        <div>
          <Link href="/" className="wordmark">
            home<span>decor.</span>
          </Link>
          <p>Make room for the little things.</p>
          <p className="muted">Home decor, thoughtfully brought together.</p>
        </div>
        <nav aria-label="Footer navigation">
          <Link href="/shop">Explore the collection</Link>
          <Link href="/shop?sort=newest">New arrivals</Link>
          <Link href="/wishlist">Your saved pieces</Link>
        </nav>
        <div>
          <p className="eyebrow">Made for everyday living</p>
          <p>Based in Bangalore, India.</p>
          <p className="muted">
            Delivery availability and timings depend on your location.
          </p>
        </div>
      </div>
      <div className="wrap footer-bottom">
        © {new Date().getFullYear()} Home Decor · A little more you, in every
        room.
      </div>
    </footer>
  );
}

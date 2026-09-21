import Link from "next/link";
export default function NotFound() {
  return (
    <section className="wrap section">
      <p className="eyebrow">404</p>
      <h1>This corner is still empty.</h1>
      <p>The page or piece you are looking for is not available.</p>
      <Link className="button button-primary" href="/shop">
        Explore the collection
      </Link>
    </section>
  );
}

"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="wrap section">
      <h1>A little pause.</h1>
      <p>We could not load this page. Please try again in a moment.</p>
      <button className="button button-primary" onClick={reset}>
        Try again
      </button>
    </section>
  );
}

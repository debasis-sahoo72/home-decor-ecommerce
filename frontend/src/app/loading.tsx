export default function Loading() {
  return (
    <div className="wrap section" role="status" aria-busy="true">
      <p>Finding beautiful things for your home…</p>
      <div className="product-grid" aria-hidden="true">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton" />
        ))}
      </div>
    </div>
  );
}

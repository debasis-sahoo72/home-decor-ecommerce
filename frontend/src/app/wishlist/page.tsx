import SavedProducts from "@/components/saved-products";
export const metadata = {
  title: "Your saved pieces",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <section className="wrap section">
      <p className="eyebrow">A little inspiration, kept close</p>
      <h1>Your saved pieces</h1>
      <p className="muted">
        Saved on this device. Clearing your browser data will remove this list.
      </p>
      <SavedProducts />
    </section>
  );
}

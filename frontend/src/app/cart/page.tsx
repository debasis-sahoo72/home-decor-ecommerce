import CartView from "@/components/cart-view";
export const metadata = {
  title: "Your bag",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <section className="wrap section">
      <p className="eyebrow">Your considered collection</p>
      <h1>Your bag</h1>
      <CartView />
    </section>
  );
}

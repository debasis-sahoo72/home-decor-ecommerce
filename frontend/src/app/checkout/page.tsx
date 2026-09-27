import CheckoutView from "@/components/checkout-view";
import "./checkout.css";
export const metadata = {
  title: "Checkout",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <section className="wrap section checkout-page">
      <p className="eyebrow">One step closer to home</p>
      <h1>A place for beautiful things.</h1>
      <CheckoutView />
    </section>
  );
}

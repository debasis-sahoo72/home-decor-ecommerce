import { OrderList } from "@/components/order-pages";
import "@/app/operations.css";
export const metadata = {
  title: "Your orders",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <section className="wrap section">
      <OrderList />
    </section>
  );
}

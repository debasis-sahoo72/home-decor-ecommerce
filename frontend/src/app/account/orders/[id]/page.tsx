import { OrderView } from "@/components/order-pages";
import "@/app/operations.css";
import { notFound } from "next/navigation";
export const metadata = {
  title: "Order details",
  robots: { index: false, follow: false },
};
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) notFound();
  return (
    <section className="wrap section">
      <OrderView id={id} />
    </section>
  );
}

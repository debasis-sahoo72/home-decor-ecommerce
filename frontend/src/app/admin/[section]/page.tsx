import AdminPanel from "@/components/admin-panel";
import { OrderList } from "@/components/order-pages";
import { notFound } from "next/navigation";
export default async function Page({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (
    ![
      "products",
      "categories",
      "inventory",
      "orders",
      "customers",
      "delivery",
      "reviews",
    ].includes(section)
  )
    notFound();
  return section === "orders" ? (
    <OrderList admin />
  ) : (
    <AdminPanel key={section} section={section} />
  );
}

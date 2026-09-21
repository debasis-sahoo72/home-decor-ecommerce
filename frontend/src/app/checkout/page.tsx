import PurchaseReview from "@/components/purchase-review";
import Link from "next/link";
export const metadata = {
  title: "Review your piece",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const q = await searchParams;
  const valid =
    typeof q.variant_id === "string" &&
    /^[0-9a-f-]{36}$/i.test(q.variant_id) &&
    typeof q.quantity === "string" &&
    /^[0-9]+$/.test(q.quantity) &&
    Number(q.quantity) >= 1 &&
    Number(q.quantity) <= 100 &&
    typeof q.pincode === "string" &&
    /^[0-9]{6}$/.test(q.pincode);
  return (
    <section className="wrap section">
      <p className="eyebrow">One step closer to home</p>
      <h1>Review your piece</h1>
      {valid ? (
        <PurchaseReview
          variantId={q.variant_id!}
          quantity={Number(q.quantity)}
          pincode={q.pincode!}
        />
      ) : (
        <div className="empty-note">
          <p>Choose a product, quantity and delivery PIN code first.</p>
          <Link href="/shop">Explore the collection →</Link>
        </div>
      )}
    </section>
  );
}

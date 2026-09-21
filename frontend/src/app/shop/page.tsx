import Shop, { Search } from "@/components/shop";
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const params = await searchParams;
  return {
    title: "Shop the collection",
    alternates: { canonical: "/shop" },
    ...(Object.keys(params).length > 0
      ? { robots: { index: false, follow: true } }
      : {}),
  };
}
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  return <Shop search={await searchParams} />;
}

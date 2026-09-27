import Shop, { Search } from "@/components/shop";
import { listingSeo, publicMetadata } from "@/lib/seo";
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const params = await searchParams;
  const seo = listingSeo("/shop", params);
  return publicMetadata({ ...seo, title: `Shop the collection${seo.suffix}`,
    description: "Find vases, textiles, lighting and thoughtful finishing touches for your home. Explore the Your Sanctuary collection." });
}
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  return <Shop search={await searchParams} />;
}

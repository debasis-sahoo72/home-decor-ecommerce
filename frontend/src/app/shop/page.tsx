import Shop, { Search } from "@/components/shop";
import { listingSeo, publicMetadata } from "@/lib/seo";
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const params = await searchParams;
  const seo = listingSeo("/shop", params);
  const offers = params.on_sale === "true";
  return publicMetadata({ ...seo, title: `${offers ? "Offers" : "Shop the collection"}${seo.suffix}`,
    description: offers ? "Explore reduced prices on home decor at Your Sanctuary. See current prices and savings on selected pieces." : "Find vases, textiles, lighting and thoughtful finishing touches for your home. Explore the Your Sanctuary collection." });
}
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const search = await searchParams;
  return <Shop search={search} />;
}

import { notFound } from "next/navigation";
import { api, ApiError, Category, ProductPage } from "@/lib/catalog";
import Shop, { Search } from "@/components/shop";
import { breadcrumbJsonLd, listingSeo, publicMetadata, siteSettings } from "@/lib/seo";
import { serializeJsonLd } from "@/lib/product-seo";
async function getCategory(slug: string) {
  try {
    return await api<Category>(`/categories/${encodeURIComponent(slug)}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}
export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Search>;
}) {
  const c = await getCategory((await params).slug);
  const search = await searchParams;
  const seo = listingSeo(`/categories/${c.slug}`, search);
  const products = await api<ProductPage>(`/products?category=${encodeURIComponent(c.slug)}&page_size=1`);
  return publicMetadata({ ...seo,
    title: `${c.seo_title || c.name}${seo.suffix}`,
    description: c.seo_description || c.description || `Explore ${c.name.toLowerCase()} and considered pieces for your home at Your Sanctuary.`,
    noindex: seo.noindex || products.total === 0,
  });
}
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Search>;
}) {
  const category = await getCategory((await params).slug);
  return (<>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(breadcrumbJsonLd([
      { name: "Home", path: "/" }, { name: "Shop", path: "/shop" },
      { name: category.name, path: `/categories/${category.slug}` },
    ], siteSettings().origin)) }} />
    <Shop
      category={category}
      search={await searchParams}
    />
  </>);
}

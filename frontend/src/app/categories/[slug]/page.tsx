import { notFound } from "next/navigation";
import { api, ApiError, Category } from "@/lib/catalog";
import Shop, { Search } from "@/components/shop";
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
  return {
    title: c.seo_title || c.name,
    description: c.seo_description || c.description,
    alternates: { canonical: `/categories/${c.slug}` },
    ...(Object.keys(search).length
      ? { robots: { index: false, follow: true } }
      : {}),
  };
}
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Search>;
}) {
  return (
    <Shop
      category={await getCategory((await params).slug)}
      search={await searchParams}
    />
  );
}

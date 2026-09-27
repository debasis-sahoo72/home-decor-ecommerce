import type { MetadataRoute } from "next";
import { api, Category, ProductPage } from "@/lib/catalog";
import { catalogPaths } from "@/lib/sitemap-catalog";
import { siteSettings } from "@/lib/seo";

export const dynamic = "force-dynamic";
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { origin, indexable } = siteSettings();
  if (!indexable) return [];
  const categories = await api<Category[]>("/categories");
  const paths = await catalogPaths(categories, (page) => api<ProductPage>(`/products?page_size=48&page=${page}&sort=newest`));
  // No invented modification dates. Failed catalog requests fail the sitemap,
  // rather than publishing a successful but incomplete list to search engines.
  return paths.map((path) => ({ url: new URL(path, origin).href }));
}

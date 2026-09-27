import type { Category, ProductPage } from "./catalog.ts";
import { isDemo } from "./media.ts";

export async function catalogPaths(categories: Category[], readPage: (page: number) => Promise<ProductPage>) {
  const paths = new Set(["/", "/shop"]);
  const populated = new Set<string>();
  let page = 1;
  let pages = 1;
  do {
    const result = await readPage(page);
    pages = result.pages;
    if (pages > 937) throw new Error("Catalog requires split sitemaps before exceeding the single-file limit.");
    for (const product of result.items) {
      if (isDemo(product.name)) continue;
      paths.add(`/product/${product.slug}`);
      populated.add(product.category.id);
    }
    page++;
  } while (page <= pages);
  for (const category of categories) {
    if (populated.has(category.id)) paths.add(`/categories/${category.slug}`);
  }
  if (paths.size > 50000) throw new Error("Split sitemap required.");
  return [...paths];
}

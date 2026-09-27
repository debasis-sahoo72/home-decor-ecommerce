import type { MetadataRoute } from "next";
import { siteSettings } from "@/lib/seo";

export const dynamic = "force-dynamic";
export default function robots(): MetadataRoute.Robots {
  const { origin, indexable } = siteSettings();
  if (!indexable) return { rules: { userAgent: "*", disallow: "/" } };
  // Private HTML remains crawlable so crawlers can see its noindex directives.
  // Authentication, not robots.txt, protects private data.
  return { rules: { userAgent: "*", allow: "/", disallow: "/api/" }, sitemap: `${origin}/sitemap.xml` };
}

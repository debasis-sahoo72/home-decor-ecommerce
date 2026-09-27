import type { Metadata } from "next";

export const brand = "Your Sanctuary";
export const defaultDescription = "Explore warm textures, considered lighting and beautiful everyday objects for your home.";
export const shareImage = { url: "/brand/primary-brand-lockup.png", alt: "Your Sanctuary — Beautiful spaces. Happier living." };

export function siteSettings(env: { SITE_URL?: string; SITE_INDEXABLE?: string } = {
  SITE_URL: process.env.SITE_URL, SITE_INDEXABLE: process.env.SITE_INDEXABLE,
}) {
  const url = new URL(env.SITE_URL || "http://127.0.0.1:3000");
  if (!/^https?:$/.test(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new Error("SITE_URL must be an HTTP(S) origin without a path or credentials.");
  }
  const indexable = env.SITE_INDEXABLE === "true";
  if (indexable && (url.protocol !== "https:" || /^(localhost|127\.|0\.0\.0\.0|\[::1\])/.test(url.hostname))) {
    throw new Error("Indexing requires a public HTTPS SITE_URL.");
  }
  return { origin: url.origin, indexable };
}

export function publicMetadata({ title, description = defaultDescription, path, images = [shareImage], noindex = false }: {
  title: string; description?: string; path: string;
  images?: { url: string; alt: string }[]; noindex?: boolean;
}): Metadata {
  const { indexable } = siteSettings();
  const fullTitle = `${title} | ${brand}`;
  return {
    title, description,
    alternates: { canonical: path },
    robots: { index: indexable && !noindex, follow: true },
    openGraph: { type: "website", locale: "en_IN", siteName: brand, title: fullTitle, description, url: path, images },
    twitter: { card: "summary_large_image", title: fullTitle, description, images },
  };
}

export function listingSeo(path: string, search: Record<string, string | string[] | undefined>) {
  const raw = search.page;
  const validPage = raw === undefined || (typeof raw === "string" && /^[1-9]\d{0,3}$/.test(raw));
  const page = validPage && raw ? Number(raw) : 1;
  const filtered = Object.keys(search).some((key) => key !== "page");
  return {
    path: page > 1 ? `${path}?page=${page}` : path,
    suffix: page > 1 ? ` — Page ${page}` : "",
    noindex: filtered || !validPage,
  };
}

export function breadcrumbJsonLd(items: { name: string; path: string }[], base: string) {
  return {
    "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem", position: i + 1, name: item.name, item: new URL(item.path, base).href,
    })),
  };
}

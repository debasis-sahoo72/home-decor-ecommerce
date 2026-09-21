import { cache } from "react";
export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string;
  seo_title: string | null;
  seo_description: string | null;
};
export type Product = {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: Category;
  seo_title: string | null;
  seo_description: string | null;
  specifications: Record<string, string>;
  price: string | null;
  in_stock: boolean;
  rating: number | null;
  review_count: number;
  images: {
    id: string;
    url: string;
    alt: string;
    width: number;
    height: number;
  }[];
  variants: {
    id: string;
    label: string;
    sku: string;
    price: string;
    compare_at_price: string | null;
    discount_percent: number;
    available_stock: number;
    in_stock: boolean;
  }[];
};
export type ProductPage = {
  items: Product[];
  total: number;
  page: number;
  pages: number;
  page_size: number;
};
export class ApiError extends Error {
  constructor(public status: number) {
    super("Catalog unavailable");
  }
}
export const api = cache(async <T>(path: string): Promise<T> => {
  const base = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  const response = await fetch(`${base}/api/v1${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.json() as Promise<T>;
});
export const money = (value: string) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number(value));
export const photos = {
  room: "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1800&q=85",
  detail:
    "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=85",
};

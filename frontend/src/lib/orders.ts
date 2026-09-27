export const statuses = [
  "PENDING_PAYMENT",
  "CONFIRMED",
  "PROCESSING",
  "PACKED",
  "SHIPPED",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
  "CANCELLED",
  "RETURN_REQUESTED",
  "RETURNED",
  "REFUNDED",
] as const;
export const statusLabel = (value: string) =>
  value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (c) => c.toUpperCase());
export const orderDate = (value: string) =>
  new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
export type OrderSummary = {
  id: string;
  number: string;
  status: string;
  total: string;
  created_at: string;
  item_count: number;
};
export type OrderDetail = OrderSummary & {
  subtotal: string;
  discount: string;
  tax: string;
  shipping_fee: string;
  address: {
    full_name?: string;
    recipient?: string;
    phone?: string;
    line1?: string;
    line2?: string;
    landmark?: string;
    city?: string;
    state?: string;
    pincode?: string;
  };
  items: {
    name: string;
    sku: string;
    quantity: number;
    unit_price: string;
    total: string;
  }[];
  history: {
    status: string;
    created_at: string;
    reason?: string;
    actor?: string;
  }[];
  allowed_transitions?: string[];
  customer?: { name: string; email: string } | null;
  payments?: { status: string; amount: string; refunded_amount: string }[];
};
export type PageData<T> = {
  items: T[];
  page: number;
  total: number;
  pages: number;
};
export async function readApi<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { cache: "no-store", signal });
  if (!response.ok) {
    if (response.status === 401) throw new Error("Please sign in to continue.");
    if (response.status === 403)
      throw new Error("Administrator access is required.");
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message || "Unable to load this information. Please retry.",
    );
  }
  return response.json();
}

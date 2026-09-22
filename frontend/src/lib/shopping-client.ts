let queue: Promise<unknown> = Promise.resolve();
export function request<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  const next = queue.then(() => mutate<T>(path, body, method));
  queue = next.catch(() => undefined);
  return next;
}
async function mutate<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  const csrf = await fetch("/api/v1/auth/csrf", {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!csrf.ok)
    throw new Error(
      "Your session could not be verified. Refresh and try again.",
    );
  const { csrf_token } = await csrf.json();
  const response = await fetch(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf_token },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.error?.message || "Please try again in a moment.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export type Delivery = {
  pincode: string;
  serviceable: boolean;
  earliest?: string;
  latest?: string;
  fee?: string;
  message: string;
};
export type Purchase = {
  name: string;
  label: string;
  quantity: number;
  price: string;
  subtotal: string;
  delivery: Delivery;
  message: string;
};
export const deliveryDate = (date: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(`${date}T12:00:00+05:30`));

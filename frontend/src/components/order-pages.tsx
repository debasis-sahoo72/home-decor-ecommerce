"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { money } from "@/lib/catalog";
import { request } from "@/lib/shopping-client";
import {
  statuses,
  statusLabel,
  orderDate,
  readApi,
  OrderSummary,
  OrderDetail,
  PageData,
} from "@/lib/orders";

export function OrderList({ admin = false }: { admin?: boolean }) {
  const [data, setData] = useState<PageData<OrderSummary> | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ page: String(page) });
    if (status) params.set("status", status);
    if (admin && query) params.set("q", query);
    if (admin && from) params.set("date_from", from);
    if (admin && to) params.set("date_to", to);
    readApi<PageData<OrderSummary>>(
      `${admin ? "/admin" : ""}/orders?${params}`,
      controller.signal,
    )
      .then((value) => {
        setData(value);
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setData(null);
          setError(e.message);
        }
      });
    return () => controller.abort();
  }, [admin, page, query, status, from, to, revision]);
  return (
    <>
      <div className="ops-heading">
        <h1>{admin ? "Orders" : "Your orders"}</h1>
        <Link className="text-link" href={admin ? "/admin" : "/shop"}>
          {admin ? "Dashboard" : "Continue shopping"}
        </Link>
      </div>
      <form
        className="ops-filters"
        onSubmit={(e) => {
          e.preventDefault();
          const values = new FormData(e.currentTarget);
          setQuery(String(values.get("q") || ""));
          setStatus(String(values.get("status") || ""));
          setFrom(String(values.get("from") || ""));
          setTo(String(values.get("to") || ""));
          setPage(1);
          setData(null);
          setRevision((v) => v + 1);
        }}
      >
        {admin && (
          <label>
            Search
            <input
              name="q"
              placeholder="Order number, customer or email"
              maxLength={100}
            />
          </label>
        )}
        <label>
          Status
          <select name="status">
            <option value="">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </label>
        {admin && (
          <>
            <label>
              From
              <input type="date" name="from" />
            </label>
            <label>
              To
              <input type="date" name="to" />
            </label>
          </>
        )}
        <button className="button button-primary">Apply filters</button>
      </form>
      {error && (
        <div role="alert" className="empty-note">
          <p>{error}</p>
          <Link href={`/login?next=${admin ? "admin" : "orders"}`}>
            Sign in
          </Link>{" "}
          <button
            className="text-button"
            onClick={() => setRevision((v) => v + 1)}
          >
            Retry
          </button>
        </div>
      )}
      {!data && !error && <p role="status">Loading orders…</p>}
      {data &&
        (data.items.length ? (
          <>
            <div className="ops-table-wrap">
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Items</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((o) => (
                    <tr key={o.id}>
                      <td>
                        <Link
                          href={`${admin ? "/admin" : "/account"}/orders/${o.id}`}
                        >
                          {o.number}
                        </Link>
                      </td>
                      <td>{orderDate(o.created_at)}</td>
                      <td>
                        <span className="order-status">
                          {statusLabel(o.status)}
                        </span>
                      </td>
                      <td>{o.item_count}</td>
                      <td>{money(o.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="ops-pagination">
              <button
                disabled={page <= 1}
                onClick={() => {
                  setPage(page - 1);
                  setData(null);
                }}
              >
                Previous
              </button>
              <span>
                Page {data.page} of {data.pages} · {data.total} orders
              </span>
              <button
                disabled={page >= data.pages}
                onClick={() => {
                  setPage(page + 1);
                  setData(null);
                }}
              >
                Next
              </button>
            </div>
          </>
        ) : (
          <div className="empty-note">
            <h2>No orders here yet.</h2>
            <p>
              {admin
                ? "Orders matching your filters will appear here."
                : "Your orders will appear here after you submit checkout."}
            </p>
          </div>
        ))}
    </>
  );
}

export function OrderView({
  id,
  admin = false,
}: {
  id: string;
  admin?: boolean;
}) {
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    readApi<OrderDetail>(`${admin ? "/admin" : ""}/orders/${id}`, c.signal)
      .then((o) => {
        setOrder(o);
        setError("");
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [id, admin, revision]);
  return (
    <>
      <Link
        className="text-link"
        href={`${admin ? "/admin" : "/account"}/orders`}
      >
        ← All orders
      </Link>
      <p role="alert">{error}</p>
      <p role="status">{notice}</p>
      {error && (
        <button onClick={() => setRevision((v) => v + 1)}>Retry</button>
      )}
      {!order && !error && <p role="status">Loading your order…</p>}
      {order && (
        <>
          <div className="ops-heading">
            <div>
              <p className="eyebrow">{orderDate(order.created_at)}</p>
              <h1>Order {order.number}</h1>
            </div>
            <span className="order-status">{statusLabel(order.status)}</span>
          </div>
          {order.status === "PENDING_PAYMENT" && (
            <p className="empty-note">
              Payment is pending. This is not a confirmed purchase. Unstarted checkout reservations expire after 30 minutes.{" "}
              {!admin && (
                <Link href={`/checkout?order=${id}`}>Resume checkout</Link>
              )}
            </p>
          )}
          {order.status === "CANCELLED" && (
            <p className="empty-note">
              Order cancelled. Cancellation does not itself confirm a refund.
            </p>
          )}
          <div className="order-detail-grid">
            <section className="ops-card">
              <h2>Your pieces</h2>
              {order.items.map((i, n) => (
                <div className="order-line" key={n}>
                  <div>
                    <strong>{i.name}</strong>
                    <small>
                      SKU {i.sku} · Quantity {i.quantity} ·{" "}
                      {money(i.unit_price)} each
                    </small>
                  </div>
                  <span>{money(i.total)}</span>
                </div>
              ))}
              <dl className="order-totals">
                <div>
                  <dt>Subtotal</dt>
                  <dd>{money(order.subtotal)}</dd>
                </div>
                <div>
                  <dt>Discount</dt>
                  <dd>−{money(order.discount)}</dd>
                </div>
                <div>
                  <dt>Delivery</dt>
                  <dd>{money(order.shipping_fee)}</dd>
                </div>
                <div>
                  <dt>Additional tax</dt>
                  <dd>{money(order.tax)}</dd>
                </div>
                <div>
                  <dt>Total</dt>
                  <dd>{money(order.total)}</dd>
                </div>
              </dl>
            </section>
            <section className="ops-card">
              <h2>Delivery address</h2>
              <address>
                {order.address.full_name || order.address.recipient}
                <br />
                {order.address.line1}
                <br />
                {order.address.line2 && (
                  <>
                    {order.address.line2}
                    <br />
                  </>
                )}
                {order.address.landmark && (
                  <>
                    {order.address.landmark}
                    <br />
                  </>
                )}
                {order.address.city}, {order.address.state}{" "}
                {order.address.pincode}
                <br />
                {order.address.phone}
              </address>
              {admin && order.customer && (
                <>
                  <h3>Customer</h3>
                  <p>
                    {order.customer.name}
                    <br />
                    {order.customer.email}
                  </p>
                </>
              )}
            </section>
          </div>
          {admin && (
            <section className="ops-card">
              <h2>Update order</h2>
              {order.allowed_transitions?.length ? (
                <form
                  key={order.status}
                  className="ops-filters"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    setBusy(true);
                    setError("");
                    setNotice("");
                    try {
                      setOrder(
                        await request<OrderDetail>(
                          `/admin/orders/${id}/status`,
                          {
                            expected_status: order.status,
                            status: f.get("status"),
                            reason: f.get("reason"),
                          },
                          "PATCH",
                        ),
                      );
                      setNotice("Order status updated.");
                    } catch (e) {
                      setError(
                        e instanceof Error
                          ? e.message
                          : "Unable to update order.",
                      );
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <label>
                    Next status
                    <select name="status" required>
                      {order.allowed_transitions.map((s) => (
                        <option value={s} key={s}>
                          {statusLabel(s)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Reason
                    <input
                      name="reason"
                      required
                      minLength={3}
                      maxLength={300}
                    />
                  </label>
                  <button className="button button-primary" disabled={busy}>
                    {busy ? "Saving…" : "Update status"}
                  </button>
                </form>
              ) : (
                <p>No manual status transitions are available.</p>
              )}
              <p className="muted">
                Payment confirmation and refunds require verified payment
                records.
              </p>
              {order.payments?.map((p, n) => (
                <p key={n}>
                  Payment: {p.status} · {money(p.amount)} · Refunded:{" "}
                  {money(p.refunded_amount)}
                </p>
              ))}
            </section>
          )}
          <section className="ops-card">
            <h2>Order history</h2>
            <ol className="order-timeline">
              {order.history.map((e, n) => (
                <li key={n}>
                  <strong>{statusLabel(e.status)}</strong>
                  <time dateTime={e.created_at}>{orderDate(e.created_at)}</time>
                  {e.reason && <p>{e.reason}</p>}
                  {e.actor && <small>{e.actor}</small>}
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </>
  );
}

import test from "node:test";
import assert from "node:assert/strict";
import { request } from "../src/lib/shopping-client.ts";

test("an expired session prevents a cart write", async (t) => {
  const calls: string[] = [];
  t.mock.method(globalThis, "fetch", async (url: string) => {
    calls.push(url);
    return new Response(null, { status: 403 });
  });
  await assert.rejects(request("/cart/items", { quantity: 1 }), /session could not be verified/);
  assert.deepEqual(calls, ["/api/v1/auth/csrf"]);
});

test("stock rejection is shown to the shopper and a later request can succeed", async (t) => {
  let writes = 0;
  t.mock.method(globalThis, "fetch", async (url: string) => {
    if (url.endsWith("/csrf")) return Response.json({ csrf_token: "test-token" });
    writes += 1;
    return writes === 1
      ? Response.json({ error: { message: "There is not enough stock." } }, { status: 409 })
      : Response.json({ quantity: 1 });
  });
  await assert.rejects(request("/cart/items", { quantity: 5 }), /not enough stock/);
  assert.deepEqual(await request("/cart/items", { quantity: 1 }), { quantity: 1 });
  assert.equal(writes, 2);
});

test("a non-JSON outage gives a useful error instead of leaking a server page", async (t) => {
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url.endsWith("/csrf")
      ? Response.json({ csrf_token: "test-token" })
      : new Response("<html>internal proxy error</html>", { status: 502 }),
  );
  await assert.rejects(request("/checkout/quote", { address_id: "test" }), /Please try again in a moment/);
});

test("removing a bag item accepts an empty successful response", async (t) => {
  t.mock.method(globalThis, "fetch", async (url: string, options?: RequestInit) => {
    if (url.endsWith("/csrf")) return Response.json({ csrf_token: "test-token" });
    assert.equal(options?.method, "DELETE");
    assert.equal(options?.body, undefined);
    assert.equal(options?.credentials, "same-origin");
    assert.equal(new Headers(options?.headers).get("X-CSRF-Token"), "test-token");
    return new Response(null, { status: 204 });
  });
  assert.equal(await request("/cart/items/test", undefined, "DELETE"), undefined);
});

test("network failure does not automatically repeat a checkout order", async (t) => {
  let attempts = 0;
  t.mock.method(globalThis, "fetch", async (url: string) => {
    if (url.endsWith("/csrf")) return Response.json({ csrf_token: "test-token" });
    attempts += 1;
    throw new TypeError("Network unavailable");
  });
  await assert.rejects(request("/checkout/orders", { idempotency_key: "test" }), /Network unavailable/);
  assert.equal(attempts, 1);
});

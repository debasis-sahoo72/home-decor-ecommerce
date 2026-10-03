"""Cross-feature API journeys, not browser E2E or live payment tests."""

from uuid import uuid4

import pytest
from test_addresses import create as add_address
from test_auth import csrf, login, register
from test_catalog import item as item_fixture
from test_checkout import gateway as gateway_fixture
from test_checkout import post, quote
from test_operations import change, promote
from test_shopping import add
from test_shopping import serviceable as serviceable_fixture

item = item_fixture
gateway = gateway_fixture
serviceable = serviceable_fixture


@pytest.mark.parametrize("captured", [True, False], ids=["captured", "failed-or-abandoned"])
def test_browse_guest_bag_login_checkout_and_fulfilment(
    client, db, item, serviceable, gateway, captured
):
    product, variant = item
    listing = client.get("/api/v1/products?q=ceramic&in_stock=true")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == str(product.id)
    detail = client.get(f"/api/v1/products/slug/{product.slug}").json()
    assert detail["variants"][0]["sku"] == variant.sku
    assert add(client, variant, 2).status_code == 201
    assert client.get("/api/v1/cart").json()["item_count"] == 2
    assert register(client).status_code == 201
    assert login(client).status_code == 200
    assert client.get("/api/v1/cart").json()["item_count"] == 2
    address = add_address(client).json()
    review = quote(client, address["id"]).json()
    assert review["cart"]["total"] == "1650.00"
    payload = {
        "address_id": address["id"],
        "quote_hash": review["quote_hash"],
        "idempotency_key": str(uuid4()),
    }
    response = client.post("/api/v1/checkout/orders", json=payload, headers=csrf(client))
    assert response.status_code == 201, response.text
    order = response.json()
    replay = client.post("/api/v1/checkout/orders", json=payload, headers=csrf(client))
    assert replay.json()["id"] == order["id"]
    assert client.get("/api/v1/orders").json()["total"] == 1
    assert post(client, order, "payment").status_code == 200
    # A browser success claim cannot establish a captured payment.
    assert post(client, order, "confirm").json()["status"] == "awaiting_payment"
    if captured:
        gateway.payment = dict(
            id="pay_fixture", order_id="order_fixture", amount=165000,
            currency="INR", status="captured", amount_refunded=0,
        )
        for _ in range(2):
            assert post(client, order, "confirm").json()["status"] == "paid"
        assert client.get("/api/v1/cart").json()["item_count"] == 0
        assert variant.inventory.on_hand == 6
        assert change(client, order["id"], "CONFIRMED", "PROCESSING").status_code == 403
        promote(db)  # Fixture setup only; no public role-grant endpoint exists.
        for source, target in [
            ("CONFIRMED", "PROCESSING"), ("PROCESSING", "PACKED"),
            ("PACKED", "SHIPPED"), ("SHIPPED", "OUT_FOR_DELIVERY"),
            ("OUT_FOR_DELIVERY", "DELIVERED"),
        ]:
            assert change(client, order["id"], source, target).status_code == 200
        result = client.get(f"/api/v1/orders/{order['id']}").json()
        assert result["status"] == "DELIVERED"
        assert result["history"][-1]["status"] == "DELIVERED"
    else:
        assert post(client, order, "confirm").json()["status"] == "awaiting_payment"
        assert client.get("/api/v1/cart").json()["item_count"] == 2
        assert variant.inventory.on_hand == 8
        promote(db)
        assert change(client, order["id"], "PENDING_PAYMENT", "CONFIRMED").status_code == 409
        assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "PENDING_PAYMENT"

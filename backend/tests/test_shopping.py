from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_auth import csrf, login, register
from test_catalog import item as catalog_item_fixture

from app.core.security import preauth_token, valid_preauth
from app.models.entities import CartItem, DeliveryPincode, Review, User
from app.services.shopping import delivery

item = catalog_item_fixture


def add(client, variant, quantity=1, **changes):
    return client.post(
        "/api/v1/cart/items",
        json={"variant_id": str(variant.id), "quantity": quantity, **changes},
        headers=csrf(client),
    )


@pytest.fixture
def serviceable(db):
    record = DeliveryPincode(
        pincode="560001",
        service="next_day",
        min_days=1,
        max_days=1,
        cutoff_hour=12,
        fee=50,
        active=True,
    )
    db.add(record)
    db.commit()
    return record


def test_cart_stock_accumulation_and_cookie(client, db, item):
    _, v = item
    response = add(client, v, 4)
    assert response.status_code == 201, response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert add(client, v, 3).status_code == 409
    assert add(client, v, 2).json()["quantity"] == 6
    cart = client.get("/api/v1/cart")
    assert cart.headers["cache-control"] == "no-store"
    assert cart.json()["items"][0]["quantity"] == 6
    assert v.inventory.reserved == 2  # Adding never reserves stock.
    entry = cart.json()["items"][0]
    assert (
        client.delete("/api/v1/cart/items/" + entry["id"], headers=csrf(client)).status_code == 204
    )
    assert client.get("/api/v1/cart").json()["items"] == []


@pytest.mark.parametrize("quantity", [0, -1, 101, 1.5, "2", True])
def test_invalid_quantity(client, item, quantity):
    assert add(client, item[1], quantity).status_code == 422


def test_cookie_tampering_and_isolation(client, db, item):
    add(client, item[1])
    item_id = str(db.scalar(select(CartItem)).id)
    client.cookies.clear()
    assert client.get("/api/v1/cart").json()["items"] == []
    assert client.delete("/api/v1/cart/items/" + item_id, headers=csrf(client)).status_code == 404
    client.cookies.set("decor-cart", "forged")
    assert client.get("/api/v1/cart").json()["items"] == []


def test_csrf_and_hidden_stock(client, db, item):
    p, v = item
    assert (
        client.post("/api/v1/cart/items", json={"variant_id": str(v.id), "quantity": 1}).status_code
        == 403
    )
    p.active = False
    db.commit()
    assert add(client, v).status_code == 404


def test_signed_cart_token_expiration():
    token = preauth_token("test:cart")
    assert valid_preauth(token, "test:cart", max_age=100)
    assert not valid_preauth(token, "wrong", max_age=100)
    assert not valid_preauth(token, "test:cart", max_age=-1)


def test_logged_in_cart_uses_session_csrf(client, item):
    register(client)
    headers = {"X-CSRF-Token": login(client).json()["csrf_token"]}
    assert (
        client.post(
            "/api/v1/cart/items",
            json={"variant_id": str(item[1].id), "quantity": 1},
            headers=headers,
        ).status_code
        == 201
    )


def test_delivery_unknown_inactive_and_invalid(client, db, serviceable):
    assert client.get("/api/v1/delivery/560001").json()["serviceable"] is True
    assert client.get("/api/v1/delivery/999999").json()["serviceable"] is False
    assert client.get("/api/v1/delivery/56001").status_code == 422
    serviceable.active = False
    db.commit()
    assert client.get("/api/v1/delivery/560001").json()["serviceable"] is False


def test_delivery_cutoff_uses_india_time(db, serviceable):
    before = delivery(db, "560001", datetime(2026, 9, 21, 6, 29, tzinfo=timezone.utc))
    after = delivery(db, "560001", datetime(2026, 9, 21, 6, 30, tzinfo=timezone.utc))
    assert before["earliest"] == "2026-09-22"
    assert after["earliest"] == "2026-09-23"


def test_buy_now_revalidates_stock_and_delivery(client, db, item, serviceable):
    _, v = item
    data = {"variant_id": str(v.id), "quantity": 2, "pincode": "560001"}

    def preview(body):
        return client.post("/api/v1/checkout/preview", json=body, headers=csrf(client))

    response = preview(data)
    assert response.status_code == 200, response.text
    assert response.json()["subtotal"] == "1600.00"
    assert preview(data | {"pincode": "999999"}).status_code == 422
    assert preview(data | {"quantity": 7}).status_code == 409
    assert preview(data | {"variant_id": str(uuid4())}).status_code == 404
    v.inventory.on_hand = 2
    db.commit()
    assert preview(data).status_code == 409


def test_only_published_reviews_no_private_email(client, db, item):
    p, _ = item
    u = User(name="Anita Customer", email="private@example.com", password_hash="test-only")
    db.add(u)
    db.flush()
    r = Review(user_id=u.id, product_id=p.id, rating=4, body="Lovely texture", status="pending")
    db.add(r)
    db.commit()
    path = f"/api/v1/products/{p.id}/reviews"
    assert client.get(path).json()["total"] == 0
    r.status = "published"
    db.commit()
    response = client.get(path)
    assert response.json()["items"][0]["author"] == "Anita"
    assert response.json()["items"][0]["body"] == "Lovely texture"
    assert "private@example.com" not in response.text
    assert client.get(path + "?page=0").status_code == 422
    p.active = False
    db.commit()
    assert client.get(path).status_code == 404

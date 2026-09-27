import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from test_addresses import create as add_address
from test_auth import csrf, login, register
from test_catalog import item as item_fixture
from test_shopping import add
from test_shopping import serviceable as serviceable_fixture

from app.api.checkout import provider
from app.core.errors import AppError
from app.models.entities import Address, Order, OrderStatusEvent, User

item = item_fixture
serviceable = serviceable_fixture


class Gateway:
    enabled = True
    key = "rzp_test_fixture"
    payment = None
    calls = 0

    def create(self, order):
        self.calls += 1
        return dict(id="order_fixture", amount=int(order.total * 100), currency="INR")

    def captured(self, provider_id):
        return self.payment


@pytest.fixture
def basket(client, item, serviceable):
    register(client)
    login(client)
    address = add_address(client).json()
    assert add(client, item[1], 2).status_code == 201
    return address


@pytest.fixture
def gateway(client):
    fixture = Gateway()
    client.app.dependency_overrides[provider] = lambda: fixture
    return fixture


def quote(client, address_id):
    return client.post(
        "/api/v1/checkout/quote", json={"address_id": address_id}, headers=csrf(client)
    )


def submit(client, address, key=None, hash=None, **extra):
    data = dict(
        address_id=address["id"],
        idempotency_key=key or str(uuid4()),
        quote_hash=hash or quote(client, address["id"]).json()["quote_hash"],
    )
    return client.post("/api/v1/checkout/orders", json=data | extra, headers=csrf(client))


def post(client, order, action):
    return client.post(f"/api/v1/checkout/orders/{order['id']}/{action}", headers=csrf(client))


def test_checkout_totals_stock_and_idempotency(client, db, item, basket, gateway):
    q = quote(client, basket["id"]).json()
    assert q["cart"]["total"] == "1650.00"
    assert q["cart"]["discount"] == "400.00"
    key = str(uuid4())
    first = submit(client, basket, key, q["quote_hash"])
    assert first.status_code == 201, first.text
    order = first.json()
    assert order["status"] == "awaiting_payment"
    assert item[1].inventory.reserved == 4
    again = submit(client, basket, key, q["quote_hash"])
    assert again.json()["id"] == order["id"]
    assert db.scalar(select(func.count()).select_from(Order)) == 1
    assert submit(client, basket, str(uuid4()), q["quote_hash"]).status_code == 409
    assert submit(client, basket, key, "a" * 64).status_code == 409
    assert post(client, order, "cancel").status_code == 200
    assert item[1].inventory.reserved == 2
    assert post(client, order, "cancel").status_code == 200


def test_tampered_totals_and_changed_prices(client, db, item, basket, gateway):
    q = quote(client, basket["id"]).json()
    assert submit(client, basket, hash=q["quote_hash"], total="1.00").status_code == 422
    item[1].price = Decimal("900.00")
    db.commit()
    assert submit(client, basket, hash=q["quote_hash"]).status_code == 409
    assert db.scalar(select(func.count()).select_from(Order)) == 0
    item[1].inventory.on_hand = 3
    db.commit()
    assert quote(client, basket["id"]).status_code == 409


def test_address_and_order_ownership(client, db, basket, gateway):
    order = submit(client, basket).json()
    other = User(name="Other", email="other@example.com", password_hash="fixture")
    db.add(other)
    db.flush()
    address = db.get(Address, basket["id"])
    address.user_id = other.id
    db.commit()
    assert quote(client, basket["id"]).status_code == 404
    db.get(Order, order["id"]).user_id = other.id
    db.commit()
    assert client.get(f"/api/v1/checkout/orders/{order['id']}").status_code == 404
    for action in ["payment", "confirm", "cancel"]:
        assert post(client, order, action).status_code == 404


def test_payment_confirmation_requires_captured_server_result(client, db, item, basket, gateway):
    order = submit(client, basket).json()
    assert post(client, order, "payment").status_code == 200
    assert post(client, order, "payment").status_code == 200
    assert gateway.calls == 1
    assert post(client, order, "cancel").status_code == 409
    assert post(client, order, "confirm").json()["status"] == "awaiting_payment"
    gateway.payment = dict(
        id="pay_fixture", order_id="order_fixture", amount=165000, currency="INR", status="captured"
    )
    assert post(client, order, "confirm").json()["status"] == "paid"
    assert post(client, order, "confirm").json()["status"] == "paid"
    assert item[1].inventory.on_hand == 6
    assert item[1].inventory.reserved == 2
    assert client.get("/api/v1/cart").json()["items"] == []
    assert (
        db.scalar(
            select(func.count())
            .select_from(OrderStatusEvent)
            .where(OrderStatusEvent.to_status == "paid")
        )
        == 1
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", 1),
        ("currency", "USD"),
        ("order_id", "order_wrong"),
        ("status", "authorized"),
        ("amount_refunded", 100),
    ],
)
def test_payment_mismatch_never_confirms(client, db, basket, gateway, field, value):
    order = submit(client, basket).json()
    post(client, order, "payment")
    gateway.payment = dict(
        id="pay_fixture", order_id="order_fixture", amount=165000, currency="INR", status="captured"
    ) | {field: value}
    assert post(client, order, "confirm").status_code == 409
    assert db.get(Order, order["id"]).status == "awaiting_payment"


def test_no_keys_no_order_and_no_reservation(client, db, item, basket):
    assert submit(client, basket).status_code == 503
    assert item[1].inventory.reserved == 2
    assert db.scalar(select(func.count()).select_from(Order)) == 0


def test_unstarted_expiry_and_unavailable_address(client, db, item, basket, gateway, serviceable):
    order = submit(client, basket).json()
    db.get(Order, order["id"]).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert post(client, order, "payment").status_code == 409
    assert item[1].inventory.reserved == 2
    serviceable.urban = False
    db.commit()
    assert quote(client, basket["id"]).status_code == 422


def test_ambiguous_provider_timeout_not_retried(client, basket, gateway):
    order = submit(client, basket).json()

    def fail(order):
        gateway.calls += 1
        raise AppError(503, "timeout", "Try status later")

    gateway.create = fail
    assert post(client, order, "payment").status_code == 503
    assert post(client, order, "payment").status_code == 409
    assert gateway.calls == 1


def test_webhook_verified_and_idempotent(client, db, item, basket, gateway):
    order = submit(client, basket).json()
    post(client, order, "payment")
    client.app.state.settings.razorpay_webhook_secret = SecretStr("webhook-test-only")
    body = json.dumps({"payload": {"payment": {"entity": {"order_id": "order_fixture"}}}}).encode()
    path = "/api/v1/payments/razorpay/webhook"
    assert client.post(path, content=body).status_code == 400
    gateway.payment = dict(
        id="pay_fixture", order_id="order_fixture", amount=165000, currency="INR", status="captured"
    )
    signature = hmac.new(b"webhook-test-only", body, hashlib.sha256).hexdigest()
    client.cookies.clear()
    for _ in range(2):
        assert (
            client.post(path, content=body, headers={"x-razorpay-signature": signature}).status_code
            == 200
        )
    assert db.get(Order, order["id"]).status == "paid"
    assert item[1].inventory.on_hand == 6


def test_checkout_requires_login_and_csrf(client):
    assert client.get("/api/v1/checkout/pending").status_code == 401
    assert client.post("/api/v1/checkout/orders", json={}).status_code == 401
    register(client)
    login(client)
    assert client.post("/api/v1/checkout/orders", json={}).status_code == 403

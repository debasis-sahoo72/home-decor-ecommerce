from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from test_auth import csrf, login, register
from test_checkout import basket as basket_fixture
from test_checkout import gateway as gateway_fixture
from test_checkout import item as item_fixture
from test_checkout import post, quote, submit
from test_checkout import serviceable as serviceable_fixture

from app.core.errors import AppError
from app.models.entities import Order, Review, User
from app.services.orders import STATUSES, validate_transition

basket = basket_fixture
gateway = gateway_fixture
item = item_fixture
serviceable = serviceable_fixture


@pytest.mark.parametrize("source", list(STATUSES.values()))
@pytest.mark.parametrize("target", list(STATUSES.values()))
def test_transition_matrix(source, target):
    allowed = {
        "awaiting_payment": {"paid", "cancelled"},
        "paid": {"processing", "cancelled"},
        "processing": {"packed", "cancelled"},
        "packed": {"shipped", "cancelled"},
        "shipped": {"out_for_delivery"},
        "out_for_delivery": {"delivered"},
        "delivered": {"return_requested"},
        "return_requested": {"returned", "delivered"},
        "returned": {"refunded"},
        "cancelled": {"refunded"},
        "refunded": set(),
    }
    if target in allowed[source]:
        validate_transition(source, target)
    else:
        with pytest.raises(AppError):
            validate_transition(source, target)


def promote(db):
    db.scalar(select(User)).role = "admin"
    db.commit()


def change(client, oid, source, target):
    return client.patch(
        f"/api/v1/admin/orders/{oid}/status",
        headers=csrf(client),
        json={"expected_status": source, "status": target, "reason": "Warehouse verified"},
    )


def captured(client, basket, gateway):
    order = submit(client, basket).json()
    assert post(client, order, "payment").status_code == 200
    gateway.payment = dict(
        id="pay_fixture", order_id="order_fixture", amount=165000, currency="INR", status="captured"
    )
    assert post(client, order, "confirm").json()["status"] == "paid"
    return order


def test_order_without_payment_and_ownership(client, db, basket, item):
    payload = dict(
        address_id=basket["id"],
        quote_hash=quote(client, basket["id"]).json()["quote_hash"],
        idempotency_key=str(uuid4()),
    )
    response = client.post("/api/v1/orders", json=payload, headers=csrf(client))
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["status"] == "PENDING_PAYMENT"
    assert order["total"] == "1650.00"
    assert (
        client.post("/api/v1/orders", json=payload, headers=csrf(client)).json()["id"]
        == order["id"]
    )
    assert item[1].inventory.reserved == 4
    assert client.get("/api/v1/orders").json()["total"] == 1
    assert "actor" not in order["history"][0]
    other = User(name="Other", email="other@example.com", password_hash="fixture")
    db.add(other)
    db.flush()
    db.get(Order, order["id"]).user_id = other.id
    db.commit()
    assert client.get(f"/api/v1/orders/{order['id']}").status_code == 404
    assert client.get("/api/v1/orders").json()["total"] == 0


def test_fulfilment_audit_filters_and_metrics(client, db, basket, gateway, item):
    order = captured(client, basket, gateway)
    promote(db)
    oid = order["id"]
    assert change(client, oid, "CONFIRMED", "SHIPPED").status_code == 409
    states = [
        "CONFIRMED",
        "PROCESSING",
        "PACKED",
        "SHIPPED",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "RETURN_REQUESTED",
        "RETURNED",
    ]
    for source, target in zip(states, states[1:]):
        response = change(client, oid, source, target)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target
        assert response.json()["history"][-1]["reason"] == "Warehouse verified"
        assert response.json()["history"][-1]["actor"].startswith("admin:")
    assert change(client, oid, "RETURNED", "REFUNDED").status_code == 409
    assert change(client, oid, "CONFIRMED", "PROCESSING").status_code == 409
    data = client.get(
        "/api/v1/admin/orders", params={"q": order["number"], "status": "RETURNED"}
    ).json()
    assert data["total"] == 1
    assert client.get("/api/v1/admin/orders?status=PACKED").json()["total"] == 0
    assert (
        client.get("/api/v1/admin/orders?date_from=2026-02-01&date_to=2026-01-01").status_code
        == 422
    )
    metrics = client.get("/api/v1/admin/dashboard").json()
    assert metrics["orders_today"] == 1
    assert metrics["revenue_today"] == "1650.00"
    assert metrics["pending_orders"] == 0
    assert metrics["low_stock_products"] == 1
    assert client.get("/api/v1/admin/inventory?low_only=true").json()["total"] == 1
    with db.begin_nested():
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE orders SET status='processing' WHERE id=:id"), {"id": oid})
        # Savepoint context is rolled back explicitly after the rejected SQL.
        db.get_nested_transaction().rollback()


@pytest.mark.parametrize("paid", [False, True])
def test_cancellation_releases_or_restocks_once(client, db, basket, gateway, item, paid):
    order = captured(client, basket, gateway) if paid else submit(client, basket).json()
    promote(db)
    source = "CONFIRMED" if paid else "PENDING_PAYMENT"
    assert change(client, order["id"], source, "CANCELLED").status_code == 200
    assert item[1].inventory.on_hand == 8
    assert item[1].inventory.reserved == 2
    assert change(client, order["id"], source, "CANCELLED").status_code == 409
    assert item[1].inventory.on_hand == 8


def test_cannot_manually_confirm_or_cancel_started_payment(client, db, basket, gateway):
    order = submit(client, basket).json()
    assert post(client, order, "payment").status_code == 200
    promote(db)
    assert change(client, order["id"], "PENDING_PAYMENT", "CONFIRMED").status_code == 409
    assert change(client, order["id"], "PENDING_PAYMENT", "CANCELLED").status_code == 409


@pytest.mark.parametrize(
    "path",
    [
        "dashboard",
        "orders",
        "inventory",
        "customers",
        "delivery",
        "reviews",
        "catalog",
        f"orders/{uuid4()}",
    ],
)
def test_admin_reads_enforce_role(client, path):
    assert client.get(f"/api/v1/admin/{path}").status_code == 401
    register(client)
    login(client)
    assert client.get(f"/api/v1/admin/{path}").status_code == 403


def test_moderation_privacy_and_write_authorization(client, db, item):
    register(client)
    login(client)
    user = db.scalar(select(User))
    review = Review(user_id=user.id, product_id=item[0].id, rating=4, body="A real fixture review")
    db.add(review)
    db.commit()
    path = f"/api/v1/admin/reviews/{review.id}"
    assert client.patch(path, json={"status": "published"}, headers=csrf(client)).status_code == 403
    assert change(client, str(uuid4()), "PENDING_PAYMENT", "CANCELLED").status_code == 403
    promote(db)
    assert client.patch(path, json={"status": "published"}).status_code == 403
    assert client.patch(path, json={"status": "published"}, headers=csrf(client)).status_code == 200
    assert client.get("/api/v1/admin/reviews?status=published").json()["total"] == 1
    user.role = "customer"
    db.add(
        User(name="Admin", email="admin@example.com", password_hash="do-not-expose", role="admin")
    )
    db.flush()
    # Inspect the API with a separate authenticated administrator dependency.
    from app.api.dependencies import require_admin

    client.app.dependency_overrides[require_admin] = lambda: db.scalar(
        select(User).where(User.role == "admin")
    )
    result = client.get("/api/v1/admin/customers").json()
    assert result["total"] == 1
    assert "password_hash" not in result["items"][0]
    assert client.get("/api/v1/admin/catalog").json()["total"] == 1

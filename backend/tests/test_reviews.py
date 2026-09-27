import pytest
from sqlalchemy import select
from test_auth import csrf, login, register
from test_checkout import basket as basket_fixture
from test_checkout import gateway as gateway_fixture
from test_checkout import item as item_fixture
from test_checkout import serviceable as serviceable_fixture
from test_operations import captured, change, promote

from app.models.entities import Order, User

basket = basket_fixture
gateway = gateway_fixture
item = item_fixture
serviceable = serviceable_fixture


@pytest.fixture
def delivered(client, db, basket, gateway):
    order = captured(client, basket, gateway)
    promote(db)
    states = ["CONFIRMED", "PROCESSING", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED"]
    for before, after in zip(states, states[1:]):
        assert change(client, order["id"], before, after).status_code == 200
    db.scalar(select(User)).role = "customer"
    db.commit()
    return order


def submit(client, item, **overrides):
    return client.post(
        f"/api/v1/products/{item[0].id}/reviews",
        headers=csrf(client),
        json=dict(rating=4, body="A carefully made vase for our home.") | overrides,
    )


def test_review_moderation_and_aggregates(client, db, item, delivered):
    path = f"/api/v1/products/{item[0].id}"
    state = client.get(path + "/review-eligibility")
    assert state.headers["cache-control"] == "no-store"
    assert state.json()["eligible"]
    response = submit(client, item)
    assert response.status_code == 201, response.text
    rid = response.json()["id"]
    assert response.json()["status"] == "pending"
    assert submit(client, item).status_code == 409
    assert client.get(path + "/reviews").json()["total"] == 0
    assert client.get(path).json()["review_count"] == 0
    moderation = f"/api/v1/admin/reviews/{rid}"
    assert (
        client.patch(moderation, headers=csrf(client), json={"status": "published"}).status_code
        == 403
    )
    promote(db)
    assert client.patch(moderation, json={"status": "published"}).status_code == 403
    assert (
        client.patch(moderation, headers=csrf(client), json={"status": "published"}).status_code
        == 200
    )
    assert client.get(path).json()["rating"] == 4
    assert client.get(path + "/reviews").json()["total"] == 1
    assert (
        client.patch(moderation, headers=csrf(client), json={"status": "rejected"}).status_code
        == 200
    )
    assert client.get(path).json()["review_count"] == 0
    assert client.get(path + "/reviews").json()["total"] == 0


def test_review_requires_delivered_owned_purchase(client, db, item, basket, gateway):
    assert submit(client, item).status_code == 403
    captured(client, basket, gateway)
    assert submit(client, item).status_code == 403


def test_another_customers_delivery_is_not_eligible(client, db, item, delivered):
    other = User(name="Other", email="review-other@example.com", password_hash="fixture")
    db.add(other)
    db.flush()
    db.get(Order, delivered["id"]).user_id = other.id
    db.commit()
    assert submit(client, item).status_code == 403


@pytest.mark.parametrize(
    "invalid",
    [
        {"rating": 0},
        {"rating": 6},
        {"rating": True},
        {"rating": 2.5},
        {"body": " " * 20},
        {"body": "x" * 2001},
        {"status": "published"},
        {"user_id": "forged"},
    ],
)
def test_review_validation(client, item, invalid):
    register(client)
    login(client)
    assert submit(client, item, **invalid).status_code == 422


def test_review_requires_login(client, item):
    assert submit(client, item).status_code == 401
    assert client.get(f"/api/v1/products/{item[0].id}/review-eligibility").status_code == 401


def test_returned_purchase_remains_eligible(client, db, item, delivered):
    promote(db)
    assert change(client, delivered["id"], "DELIVERED", "RETURN_REQUESTED").status_code == 200
    assert submit(client, item).status_code == 403  # Admins cannot create reviews.
    db.scalar(select(User)).role = "customer"
    db.commit()
    assert submit(client, item).status_code == 201


def test_inactive_and_unknown_products(client, db, item, delivered):
    from uuid import uuid4

    assert client.get(f"/api/v1/products/{uuid4()}/review-eligibility").status_code == 404
    item[0].active = False
    db.commit()
    assert submit(client, item).status_code == 404


def test_review_creation_requires_csrf(client, item, delivered):
    assert (
        client.post(
            f"/api/v1/products/{item[0].id}/reviews",
            json={"rating": 5, "body": "Lovely product for the living room."},
        ).status_code
        == 403
    )

from uuid import uuid4

import pytest
from test_auth import csrf, login, register

DATA = dict(
    full_name="Test Customer",
    phone="9876543210",
    line1="12 Sample Road",
    line2="Apartment 4",
    landmark="Sample park",
    city="Bengaluru",
    state="Karnataka",
    country="IN",
    pincode="560001",
)


def create(client, **changes):
    return client.post("/api/v1/addresses", json=DATA | changes, headers=csrf(client))


@pytest.fixture
def customer(client):
    register(client)
    login(client)
    return client


def test_address_crud_default_and_private_response(customer):
    first = create(customer)
    assert first.status_code == 201, first.text
    a = first.json()
    assert a["is_default"] is True
    assert a["phone"] == "+919876543210"
    assert "user_id" not in a
    second = create(customer, line1="34 Other Road")
    assert second.status_code == 201
    b = second.json()
    assert b["is_default"] is False
    assert customer.get("/api/v1/addresses/" + a["id"]).json()["landmark"] == "Sample park"
    edit = customer.put(
        "/api/v1/addresses/" + a["id"],
        json=DATA | {"city": "Mysuru", "line2": None, "landmark": ""},
        headers=csrf(customer),
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["city"] == "Mysuru"
    assert edit.json()["landmark"] is None
    assert edit.json()["is_default"] is True
    response = customer.post("/api/v1/addresses/" + b["id"] + "/default", headers=csrf(customer))
    assert response.status_code == 200
    rows = customer.get("/api/v1/addresses")
    assert rows.headers["cache-control"] == "no-store"
    assert sum(x["is_default"] for x in rows.json()) == 1
    assert rows.json()[0]["id"] == b["id"]
    assert (
        customer.delete("/api/v1/addresses/" + b["id"], headers=csrf(customer)).status_code == 204
    )
    assert customer.get("/api/v1/addresses").json()[0]["is_default"] is True
    assert (
        customer.delete("/api/v1/addresses/" + a["id"], headers=csrf(customer)).status_code == 204
    )
    assert customer.get("/api/v1/addresses").json() == []


def test_other_customer_cannot_read_edit_delete_or_default(customer):
    target = create(customer).json()["id"]
    customer.cookies.clear()
    register(customer, email="other@example.com")
    login(customer, email="other@example.com")
    assert customer.get("/api/v1/addresses").json() == []
    assert customer.get("/api/v1/addresses/" + target).status_code == 404
    assert (
        customer.put("/api/v1/addresses/" + target, json=DATA, headers=csrf(customer)).status_code
        == 404
    )
    assert (
        customer.post(
            "/api/v1/addresses/" + target + "/default", headers=csrf(customer)
        ).status_code
        == 404
    )
    assert customer.delete("/api/v1/addresses/" + target, headers=csrf(customer)).status_code == 404
    customer.cookies.clear()
    login(customer)
    assert customer.get("/api/v1/addresses/" + target).json()["line1"] == DATA["line1"]


def test_auth_csrf_and_owner_injection(client, customer):
    assert customer.post("/api/v1/addresses", json=DATA).status_code == 403
    assert create(customer, user_id=str(uuid4())).status_code == 422
    customer.cookies.clear()
    assert customer.get("/api/v1/addresses").status_code == 401
    assert customer.post("/api/v1/addresses", json=DATA, headers=csrf(customer)).status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        dict(full_name=" "),
        dict(phone="1234567890"),
        dict(phone="+12025550123"),
        dict(phone="98765abc10"),
        dict(pincode="012345"),
        dict(pincode="56000"),
        dict(pincode="56000a"),
        dict(country="US"),
        dict(line1=""),
        dict(city=" "),
        dict(state=" "),
        dict(landmark="x" * 201),
        dict(is_default="yes"),
        dict(line2="abc\nxyz"),
    ],
)
def test_invalid_addresses(customer, change):
    assert create(customer, **change).status_code == 422


def test_create_new_default_and_normalize(customer):
    create(customer)
    new = create(customer, is_default=True, full_name="  Another Name  ", phone="+91 98765 43210")
    assert new.status_code == 201, new.text
    assert new.json()["full_name"] == "Another Name"
    rows = customer.get("/api/v1/addresses").json()
    assert sum(x["is_default"] for x in rows) == 1
    assert rows[0]["id"] == new.json()["id"]


def test_address_limit(customer):
    for _ in range(20):
        assert create(customer).status_code == 201
    assert create(customer).status_code == 422

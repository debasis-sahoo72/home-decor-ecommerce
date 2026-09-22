from decimal import Decimal
from uuid import uuid4

import pytest
from test_auth import csrf, login, register
from test_catalog import item as catalog_item_fixture
from test_shopping import add
from test_shopping import serviceable as delivery_fixture

item = catalog_item_fixture
serviceable = delivery_fixture


def test_cart_totals_current_prices_and_delivery(client, db, item, serviceable):
    _, variant = item
    assert add(client, variant, 2).status_code == 201
    cart = client.get("/api/v1/cart").json()
    assert cart["subtotal"] == "2000.00"
    assert cart["discount"] == "400.00"
    assert cart["merchandise_total"] == "1600.00"
    assert cart["total"] is None
    assert client.get("/api/v1/cart?pincode=560001").json()["total"] == "1650.00"
    assert client.get("/api/v1/cart?pincode=999999").json()["total"] is None
    assert client.get("/api/v1/cart?pincode=bad").status_code == 422
    variant.price = Decimal("750.25")
    db.commit()
    assert client.get("/api/v1/cart").json()["merchandise_total"] == "1500.50"
    assert add(client, variant, price="0.01").status_code == 422


def test_cart_update_clear_and_unavailable(client, db, item):
    product, variant = item
    add(client, variant)
    entry = client.get("/api/v1/cart").json()["items"][0]
    path = "/api/v1/cart/items/" + entry["id"]
    assert client.patch(path, json={"quantity": 6}, headers=csrf(client)).status_code == 204
    assert client.patch(path, json={"quantity": 7}, headers=csrf(client)).status_code == 409
    assert (
        client.patch(path, json={"quantity": 2, "price": 1}, headers=csrf(client)).status_code
        == 422
    )
    product.active = False
    db.commit()
    cart = client.get("/api/v1/cart").json()
    assert cart["stock_valid"] is False
    assert cart["items"][0]["available_stock"] == 0
    assert client.delete("/api/v1/cart", headers=csrf(client)).status_code == 204
    assert client.get("/api/v1/cart").json()["item_count"] == 0


@pytest.mark.parametrize("quantity", [0, -1, 101, 1.2, True, "2"])
def test_patch_rejects_invalid_quantity(client, item, quantity):
    add(client, item[1])
    entry = client.get("/api/v1/cart").json()["items"][0]
    assert (
        client.patch(
            "/api/v1/cart/items/" + entry["id"], json={"quantity": quantity}, headers=csrf(client)
        ).status_code
        == 422
    )


def test_account_cart_merge_stock_cap_persistence_and_isolation(client, item):
    register(client)
    login(client)
    add(client, item[1], 4)
    client.post("/api/v1/auth/logout", headers=csrf(client))
    assert client.get("/api/v1/cart").json()["items"] == []
    add(client, item[1], 4)
    assert login(client).status_code == 200
    cart = client.get("/api/v1/cart").json()
    assert cart["owner"] == "account"
    assert cart["items"][0]["quantity"] == 6
    entry_id = cart["items"][0]["id"]
    assert not client.cookies.get("decor-cart")
    client.cookies.clear()
    login(client)
    assert client.get("/api/v1/cart").json()["items"][0]["id"] == entry_id
    client.cookies.clear()
    register(client, email="second@example.com")
    login(client, email="second@example.com")
    assert client.get("/api/v1/cart").json()["items"] == []
    assert (
        client.patch(
            "/api/v1/cart/items/" + entry_id, json={"quantity": 1}, headers=csrf(client)
        ).status_code
        == 404
    )
    assert client.delete("/api/v1/cart/items/" + entry_id, headers=csrf(client)).status_code == 404


def test_invalid_variant_and_csrf(client):
    assert (
        client.post(
            "/api/v1/cart/items",
            json={"variant_id": str(uuid4()), "quantity": 1},
            headers=csrf(client),
        ).status_code
        == 404
    )
    assert client.delete("/api/v1/cart").status_code == 403
    assert (
        client.patch("/api/v1/cart/items/" + str(uuid4()), json={"quantity": 1}).status_code == 403
    )


def test_wishlist_auth_duplicates_and_persistence(client, item):
    product, _ = item
    path = "/api/v1/wishlist"
    data = {"product_id": str(product.id)}
    assert client.get(path).status_code == 401
    register(client)
    login(client)
    assert client.post(path + "/items", json=data).status_code == 403
    for _ in range(2):
        response = client.post(path + "/items", json=data, headers=csrf(client))
        assert response.status_code == 200, response.text
        assert response.json()["product_ids"] == [str(product.id)]
    client.cookies.clear()
    login(client)
    response = client.get(path)
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"][0]["id"] == str(product.id)
    assert (
        client.delete(path + "/items/" + str(product.id), headers=csrf(client)).status_code == 204
    )
    assert client.get(path).json()["items"] == []


def test_wishlist_inactive_merge_and_isolation(client, db, item):
    product, _ = item
    register(client)
    login(client)
    response = client.post(
        "/api/v1/wishlist/merge",
        json={"product_ids": [str(product.id), str(product.id), str(uuid4())]},
        headers=csrf(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["product_ids"] == [str(product.id)]
    product.active = False
    db.commit()
    response = client.get("/api/v1/wishlist").json()
    assert response["items"] == []
    assert response["unavailable_ids"] == [str(product.id)]
    assert (
        client.post(
            "/api/v1/wishlist/items", json={"product_id": str(product.id)}, headers=csrf(client)
        ).status_code
        == 404
    )
    client.cookies.clear()
    register(client, email="second@example.com")
    login(client, email="second@example.com")
    assert client.get("/api/v1/wishlist").json()["product_ids"] == []
    client.delete("/api/v1/wishlist/items/" + str(product.id), headers=csrf(client))
    client.cookies.clear()
    login(client)
    assert client.get("/api/v1/wishlist").json()["product_ids"] == [str(product.id)]
    client.delete("/api/v1/wishlist/items/" + str(product.id), headers=csrf(client))
    assert client.get("/api/v1/wishlist").json()["product_ids"] == []

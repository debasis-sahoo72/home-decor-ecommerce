from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_auth import login, register

from app.models.entities import Category, Inventory, Product, ProductVariant, User


@pytest.fixture
def admin_headers(client, db):
    register(client)
    db.scalar(select(User)).role = "admin"
    db.commit()
    return {"X-CSRF-Token": login(client).json()["csrf_token"]}


@pytest.fixture
def item(db):
    c = Category(name="Vases", slug="vases")
    p = Product(
        category=c,
        name="Ceramic Vase",
        slug="ceramic-vase",
        description="Handmade ceramic vessel",
        specifications={"Material": "Clay"},
    )
    v = ProductVariant(
        product=p,
        sku="VASE-01",
        label="Sand",
        price=Decimal("800.00"),
        compare_at_price=Decimal("1000.00"),
    )
    v.inventory = Inventory(on_hand=8, reserved=2)
    db.add(p)
    db.commit()
    return p, v


def test_public_detail_and_decimal_discount(client, item):
    p, v = item
    r = client.get(f"/api/v1/products/{p.id}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["price"] == "800.00"
    assert data["variants"][0]["discount_percent"] == 20
    assert data["variants"][0]["available_stock"] == 6
    assert data["rating"] is None and data["review_count"] == 0
    assert client.get("/api/v1/products/slug/ceramic-vase").json()["id"] == str(p.id)
    assert client.get("/api/v1/categories/vases").status_code == 200
    assert len(client.get("/api/v1/categories").json()) == 1


@pytest.mark.parametrize(
    "query,total",
    [
        ("q=ceramic", 1),
        ("q=lighting", 0),
        ("category=vases", 1),
        ("category=lighting", 0),
        ("min_price=801", 0),
        ("max_price=800", 1),
        ("in_stock=true", 1),
        ("featured=true", 0),
        ("sort=best_sellers", 0),
        ("q=%25", 0),
    ],
)
def test_search_filters(client, item, query, total):
    r = client.get(f"/api/v1/products?{query}")
    assert r.status_code == 200, r.text
    assert r.json()["total"] == total


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=49",
        "sort=random",
        "min_price=-1",
        "min_price=100&max_price=50",
        "min_price=NaN",
    ],
)
def test_invalid_query(client, query):
    assert client.get(f"/api/v1/products?{query}").status_code == 422


@pytest.mark.parametrize("target", ["product", "category", "variant", "archive"])
def test_inactive_hidden(client, db, item, target):
    p, v = item
    if target == "product":
        p.active = False
    elif target == "category":
        p.category.active = False
    elif target == "variant":
        v.active = False
    else:
        from datetime import UTC, datetime

        p.archived_at = datetime.now(UTC)
    db.commit()
    assert client.get(f"/api/v1/products/{p.id}").status_code == 404
    assert client.get("/api/v1/products").json()["total"] == 0


def test_same_variant_price_stock_filter(client, db, item):
    p, v = item
    v.inventory.on_hand = v.inventory.reserved
    expensive = ProductVariant(product=p, sku="VASE-02", label="Large", price=Decimal("2000"))
    expensive.inventory = Inventory(on_hand=10, reserved=0)
    db.add(expensive)
    db.commit()
    assert client.get("/api/v1/products?max_price=1000&in_stock=true").json()["total"] == 0


def test_sort_and_pagination(client, db, item):
    p, _ = item
    other = Product(category=p.category, name="Amber Vase", slug="amber-vase")
    v = ProductVariant(product=other, sku="AMBER", label="Default", price=Decimal("100"))
    v.inventory = Inventory(on_hand=1, reserved=0)
    db.add(other)
    db.commit()
    r = client.get("/api/v1/products?sort=price_asc&page_size=1").json()
    assert r["total"] == 2 and r["pages"] == 2 and r["items"][0]["id"] == str(other.id)
    assert client.get("/api/v1/products?sort=price_desc").json()["items"][0]["id"] == str(p.id)
    assert client.get("/api/v1/products?sort=name").json()["items"][0]["id"] == str(other.id)
    assert client.get("/api/v1/products?sort=price_asc&page_size=1&page=2").json()["items"][0][
        "id"
    ] == str(p.id)


def test_write_requires_admin_and_csrf(client, item):
    assert (
        client.post("/api/v1/admin/categories", json={"name": "New", "slug": "new"}).status_code
        == 401
    )
    register(client)
    headers = {"X-CSRF-Token": login(client).json()["csrf_token"]}
    assert (
        client.post(
            "/api/v1/admin/categories", headers=headers, json={"name": "New", "slug": "new"}
        ).status_code
        == 403
    )


def test_admin_creation_update_duplicates(client, db, admin_headers):
    payload = {"name": "Lighting", "slug": "lighting"}
    assert client.post("/api/v1/admin/categories", json=payload).status_code == 403
    c = client.post("/api/v1/admin/categories", json=payload, headers=admin_headers)
    assert c.status_code == 201, c.text
    assert (
        client.post("/api/v1/admin/categories", json=payload, headers=admin_headers).status_code
        == 409
    )
    data = {"name": "Table Lamp", "slug": "table-lamp", "category_id": c.json()["id"]}
    p = client.post("/api/v1/admin/products", json=data, headers=admin_headers)
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    assert client.get(f"/api/v1/products/{pid}").status_code == 404  # No active variant yet.
    assert (
        client.post("/api/v1/admin/products", json=data, headers=admin_headers).status_code == 409
    )
    vd = {"sku": "LAMP-01", "label": "Standard", "price": "999.99", "compare_at_price": "1200"}
    v = client.post(f"/api/v1/admin/products/{pid}/variants", json=vd, headers=admin_headers)
    assert v.status_code == 201, v.text
    vid = v.json()["id"]
    assert (
        client.post(
            f"/api/v1/admin/products/{pid}/variants", json=vd, headers=admin_headers
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/admin/variants/{vid}/stock", json={"on_hand": 5}, headers=admin_headers
        ).json()["available_stock"]
        == 5
    )
    assert (
        client.put(
            f"/api/v1/admin/products/{pid}", json=data | {"active": False}, headers=admin_headers
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/products/{pid}").status_code == 404


@pytest.mark.parametrize(
    "change", [{"price": "-1"}, {"price": "1.001"}, {"compare_at_price": "1"}, {"sku": "bad sku"}]
)
def test_variant_validation(client, item, admin_headers, change):
    p, _ = item
    data = {"sku": "OTHER", "label": "Small", "price": "100", "compare_at_price": "200"} | change
    assert (
        client.post(
            f"/api/v1/admin/products/{p.id}/variants", json=data, headers=admin_headers
        ).status_code
        == 422
    )


def test_stock_reservations_and_unknown(client, item, admin_headers):
    _, v = item
    path = f"/api/v1/admin/variants/{v.id}/stock"
    assert client.put(path, json={"on_hand": -1}, headers=admin_headers).status_code == 422
    assert client.put(path, json={"on_hand": 1}, headers=admin_headers).status_code == 409
    assert (
        client.put(path, json={"on_hand": 4}, headers=admin_headers).json()["available_stock"] == 2
    )
    assert client.get(f"/api/v1/products/{uuid4()}").status_code == 404


def test_images(client, item, admin_headers):
    p, _ = item
    path = f"/api/v1/admin/products/{p.id}/images"
    data = {
        "public_id": "test/vase",
        "url": "https://res.cloudinary.com/test/image/upload/vase.jpg",
        "alt": "Sand ceramic vase",
        "position": 0,
        "width": 800,
        "height": 1000,
    }
    r = client.post(path, json=data, headers=admin_headers)
    assert r.status_code == 410, r.text
    assert (
        client.post(
            path, json=data | {"url": "http://localhost/private"}, headers=admin_headers
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/v1/admin/images/{uuid4()}",
            json=data | {"alt": "Updated alt"},
            headers=admin_headers,
        ).status_code
        == 410
    )
    assert client.get(f"/api/v1/products/{p.id}").json()["images"] == []
    assert (
        client.delete(f"/api/v1/admin/images/{uuid4()}", headers=admin_headers).status_code
        == 410
    )


def test_bad_slug_and_category(client, item, admin_headers):
    assert (
        client.post(
            "/api/v1/admin/categories",
            json={"name": "Bad", "slug": "Bad Slug"},
            headers=admin_headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/admin/products",
            json={"name": "Missing", "slug": "missing", "category_id": str(uuid4())},
            headers=admin_headers,
        ).status_code
        == 404
    )


def test_published_ratings_and_paid_best_sellers(client, db, item):
    from app.models.entities import Order, OrderItem, Review

    p, v = item
    user = User(email="reviewer@example.com", name="Reviewer", password_hash="test-only")
    db.add(user)
    db.flush()
    review = Review(
        user_id=user.id, product_id=p.id, rating=4, body="Review fixture", status="pending"
    )
    order = Order(
        number="TEST-CATALOG-001",
        status="awaiting_payment",
        subtotal=1600,
        shipping_fee=0,
        tax=0,
        discount=0,
        total=1600,
        shipping_snapshot={},
        delivery_snapshot={},
    )
    order.items = [OrderItem(variant_id=v.id, sku=v.sku, name=p.name, quantity=2, unit_price=800)]
    db.add_all([review, order])
    db.commit()
    assert client.get(f"/api/v1/products/{p.id}").json()["review_count"] == 0
    assert client.get("/api/v1/products?sort=best_sellers").json()["total"] == 0
    review.status = "published"
    order.status = "paid"
    db.commit()
    result = client.get("/api/v1/products?sort=best_sellers").json()
    assert result["total"] == 1
    assert result["items"][0]["rating"] == 4.0
    assert result["items"][0]["review_count"] == 1
    order.status = "cancelled"
    db.commit()
    assert client.get("/api/v1/products?sort=best_sellers").json()["total"] == 0

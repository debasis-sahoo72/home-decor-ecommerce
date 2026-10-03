from decimal import Decimal

from test_catalog import item as item_fixture

from app.models.entities import Inventory, ProductVariant

item = item_fixture


def test_offers_require_an_active_discounted_variant(client, db, item):
    variant = item[1]
    for compare, expected in [(None, 0), (variant.price, 0), (Decimal("1000"), 1)]:
        variant.compare_at_price = compare
        db.commit()
        assert client.get("/api/v1/products?on_sale=true").json()["total"] == expected
    variant.active = False
    db.commit()
    assert client.get("/api/v1/products?on_sale=true").json()["total"] == 0


def test_offer_stock_and_price_filters_match_same_variant(client, db, item):
    item[1].inventory.on_hand = item[1].inventory.reserved
    other = ProductVariant(product=item[0], sku="FULL-PRICE", label="Other", price=Decimal("100"))
    other.inventory = Inventory(on_hand=10, reserved=0)
    db.add(other)
    db.commit()
    assert client.get("/api/v1/products?on_sale=true").json()["total"] == 1
    for sort in ["price_asc", "price_desc", "newest"]:
        response = client.get(f"/api/v1/products?on_sale=true&sort={sort}")
        assert response.status_code == 200, response.text
        offer = response.json()["items"][0]
        assert offer["price"] == "800.00"
        assert len(offer["variants"]) == 1
        assert Decimal(offer["variants"][0]["compare_at_price"]) > Decimal(offer["price"])
        assert offer["in_stock"] is False
    assert client.get("/api/v1/products?on_sale=true&in_stock=true").json()["total"] == 0
    assert client.get("/api/v1/products?on_sale=true&max_price=200").json()["total"] == 0
    assert "featured" not in client.get(f"/api/v1/products/{item[0].id}").json()

"""Query-growth checks; elapsed times are diagnostic, not flaky CI thresholds."""

import json
from time import perf_counter

import pytest
from sqlalchemy import event

from app.api.catalog import admin_products
from app.models.entities import Cart, CartItem, Category, Inventory, Product, ProductVariant
from app.schemas.catalog import CatalogQuery
from app.services import catalog, shopping


@pytest.mark.parametrize("size", [1, 24])
def test_read_query_growth(db, size):
    category = Category(name="Performance fixtures", slug="performance-fixtures")
    cart = Cart(guest_token_hash="a" * 64)
    db.add_all([category, cart])
    db.flush()
    for i in range(size):
        product = Product(category=category, name=f"Vase {i}", slug=f"perf-vase-{i}")
        variant = ProductVariant(product=product, sku=f"PERF-{i}", label="Sand", price=100)
        variant.inventory = Inventory(on_hand=10, reserved=0)
        db.add(variant)
        db.flush()
        db.add(CartItem(cart_id=cart.id, variant_id=variant.id, quantity=1))
    db.flush()
    connection = db.connection()
    for name, call in [
        ("cart", lambda: shopping.cart_items(db, token_hash="a" * 64)),
        ("catalog", lambda: catalog.listing(db, CatalogQuery(page_size=48))),
        ("admin_catalog", lambda: admin_products(page=1, db=db)),
    ]:
        db.expunge_all()  # A warm identity map would hide per-row lazy queries.
        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(connection, "before_cursor_execute", record)
        start = perf_counter()
        try:
            result = call()
        finally:
            elapsed = (perf_counter() - start) * 1000
            event.remove(connection, "before_cursor_execute", record)
        rows = result if isinstance(result, list) else result["items"]
        assert len(rows) == size
        assert len(statements) <= {"cart": 7, "catalog": 7, "admin_catalog": 5}[name]
        print(json.dumps({"path": name, "products": size, "selects": len(statements),
                          "ms": round(elapsed, 2), "json_bytes": len(json.dumps(result).encode())}))

from sqlalchemy import func, select

from app.models.entities import DeliveryPincode, Product, ProductVariant, Review
from app.seed_demo import seed_demo


def test_demo_catalog_is_labelled_idempotent_and_has_no_fake_reviews(db, client):
    assert seed_demo(db) == 6
    assert seed_demo(db) == 0
    db.commit()
    products = client.get("/api/v1/products").json()
    assert products["total"] == 6
    assert all(p["name"].startswith("[DEMO]") for p in products["items"])
    for product in products["items"]:
        assert len(product["images"]) == 4
        assert len({i["url"] for i in product["images"]}) == 4
        assert all("AI-created demo" in i["alt"] for i in product["images"])
        assert all(
            i["url"].startswith("https://local-preview.invalid/demo/") for i in product["images"]
        )
        assert "LOCAL PREVIEW ONLY" in product["description"]
    assert client.get("/api/v1/products?on_sale=true").json()["total"] == 3
    assert client.get("/api/v1/products?sort=newest").json()["total"] == 6
    assert db.scalar(select(func.count()).select_from(Review)) == 0
    assert db.scalar(select(func.count()).select_from(DeliveryPincode)) == 0
    assert db.scalar(select(func.count()).select_from(ProductVariant)) == 6
    assert db.scalar(select(func.count()).select_from(Product)) == 6


def test_refresh_keeps_inventory_and_existing_image_ids(db):
    seed_demo(db)
    product = db.scalar(select(Product).where(Product.slug == "demo-ceramic-vase"))
    variant = product.variants[0]
    variant.inventory.on_hand = 8
    ids = {image.id for image in product.images}
    assert seed_demo(db) == 0
    assert variant.inventory.on_hand == 8
    assert {image.id for image in product.images} == ids


def test_refresh_does_not_overwrite_non_demo_product(db):
    seed_demo(db)
    product = db.scalar(select(Product).where(Product.slug == "demo-ceramic-vase"))
    product.name = "Real vase"
    product.description = "Owner supplied description"
    seed_demo(db)
    assert product.description == "Owner supplied description"

"""Opt-in local preview catalog: python -m app.seed_demo. Never run in production."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import SessionLocal
from app.models.entities import Category, Inventory, Product, ProductImage, ProductVariant

DEMO_ITEMS = [
    ("ceramic-vase", "Ceramic Vase", "decor-objects", "Decor objects", "1290", "1590"),
    ("woven-basket", "Woven Storage Basket", "decor-objects", "Decor objects", "1890", None),
    ("linen-cushion", "Linen Cushion", "textiles", "Textiles", "890", "1190"),
    ("cotton-throw", "Cotton Throw", "textiles", "Textiles", "2190", None),
    ("table-lamp", "Warm Table Lamp", "lighting", "Lighting", "3490", "3990"),
    ("pendant-light", "Pendant Light", "lighting", "Lighting", "4290", None),
]
DETAILS = {
    "ceramic-vase": (
        "A sculptural ivory vase with a softly rounded silhouette and a speckled matte finish. A quiet statement for a console, shelf or bedside table.",
        "Ceramic",
        "Ivory",
        "28 × 16 cm",
        "Wipe with a soft, dry cloth.",
    ),
    "woven-basket": (
        "Natural woven texture meets a graphic charcoal stripe. This roomy basket brings a relaxed, considered feel to blankets, books and everyday essentials.",
        "Seagrass",
        "Natural / charcoal",
        "35 × 30 cm",
        "Dust gently; keep away from moisture.",
    ),
    "linen-cushion": (
        "A muted sage cushion with fine piping and a beautifully tactile weave. Layer it with warm neutrals for an inviting place to slow down.",
        "Linen blend",
        "Sage green",
        "45 × 45 cm",
        "Gentle cold wash for the removable cover.",
    ),
    "cotton-throw": (
        "Soft oatmeal tones, caramel stripes and a generous fringe. Drape this textured throw across a sofa or the end of a bed for an effortless finishing touch.",
        "Cotton",
        "Oatmeal / caramel",
        "130 × 170 cm",
        "Gentle cold wash; dry flat.",
    ),
    "table-lamp": (
        "An earthy terracotta base paired with an ivory fabric shade. Its rounded silhouette adds warmth to a reading corner, console or bedside.",
        "Ceramic / linen shade",
        "Terracotta / ivory",
        "42 × 28 cm",
        "Dust with a dry cloth; unplug before cleaning.",
    ),
    "pendant-light": (
        "An airy woven shade with a softly flared profile. Natural texture and warm tones make this pendant an inviting focal point above a table.",
        "Woven rattan",
        "Natural",
        "38 × 32 cm",
        "Dust gently; professional fitting recommended.",
    ),
}
VIEWS = [
    ("front", "front view"),
    ("side", "alternate angle"),
    ("detail", "material close-up"),
    ("styled", "styled room setting"),
]


def seed_demo(db):
    created = 0
    for slug, name, category_slug, category_name, price, compare in DEMO_ITEMS:
        product = db.scalar(select(Product).where(Product.slug == "demo-" + slug))
        # Never overwrite a real product that happens to use the same slug.
        if product is not None and (
            not product.name.startswith("[DEMO]")
            or product.specifications.get("Catalog") != "Demo data for local preview"
        ):
            continue
        if product is None:
            category = db.scalar(select(Category).where(Category.slug == category_slug))
            if category is None:
                category = Category(name=category_name, slug=category_slug)
                db.add(category)
            product = Product(
                category=category,
                name=f"[DEMO] {name}",
                slug="demo-" + slug,
                active=True,
            )
            variant = ProductVariant(
                product=product,
                sku="DEMO-" + slug.upper(),
                label=DETAILS[slug][2],
                price=Decimal(price),
                compare_at_price=Decimal(compare) if compare else None,
            )
            variant.inventory = Inventory(on_hand=12, reserved=0)
            db.add(product)
            created += 1
        description, material, colour, dimensions, care = DETAILS[slug]
        for variant in product.variants:
            if variant.label == "Sample option":
                variant.label = colour
        product.description = (
            description
            + "\n\nLOCAL PREVIEW ONLY. AI-created sample imagery, illustrative prices, dimensions and stock. Not actual sale inventory. Styling accessories are not included."
        )
        product.specifications = {
            "Catalog": "Demo data for local preview",
            "Material (sample)": material,
            "Colour (sample)": colour,
            "Dimensions (sample)": dimensions,
            "Care (sample)": care,
            "Photography": "AI-created demo imagery; not actual product photography",
        }
        for position, (view, label) in enumerate(VIEWS):
            # Update existing image rows in place; preserve product, variant, cart and stock IDs.
            image = next((i for i in product.images if i.position == position), None)
            if image is None:
                image = ProductImage(position=position)
                product.images.append(image)
            image.public_id = f"local-demo/{slug}/{view}"
            image.url = f"https://local-preview.invalid/demo/{slug}-{view}.png"
            image.alt = f"AI-created demo {name.lower()}, {label}; illustrative product photography"
            image.width = 1122
            image.height = 1402
    db.flush()
    return created


def main():
    settings = get_settings()
    if settings.app_env != "development" or make_url(settings.database_url).host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise SystemExit("Demo seeding is restricted to development on a local PostgreSQL host.")
    with SessionLocal.begin() as db:
        created = seed_demo(db)
    print(
        f"Created {created} demo products; refreshed demo descriptions and four-image galleries. No reviews or delivery promises were added."
    )


if __name__ == "__main__":
    main()

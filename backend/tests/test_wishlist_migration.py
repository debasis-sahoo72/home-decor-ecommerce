from uuid import uuid4

from alembic.config import Config
from sqlalchemy import insert, text

from alembic import command
from app.models.entities import Category, Product, ProductVariant, User, Wishlist


def test_product_wishlist_migration_preserves_and_deduplicates(pg_engine):
    # Exercise real PostgreSQL DDL and fixture data, then roll the entire test back.
    with pg_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.downgrade(config, "0002")
            user, category, product, wishlist = [uuid4() for _ in range(4)]
            connection.execute(
                insert(User).values(
                    id=user,
                    email="migration@example.com",
                    name="Migration test",
                    password_hash="not-a-login",
                )
            )
            connection.execute(
                insert(Category).values(
                    id=category, name="Migration category", slug="migration-category"
                )
            )
            connection.execute(
                insert(Product).values(
                    id=product,
                    category_id=category,
                    name="Migration product",
                    slug="migration-product",
                    description="Test",
                )
            )
            connection.execute(insert(Wishlist).values(id=wishlist, user_id=user))
            for index in range(2):
                variant = uuid4()
                connection.execute(
                    insert(ProductVariant).values(
                        id=variant,
                        product_id=product,
                        sku=f"MIGRATE-{index}",
                        label=f"Option {index}",
                        price=10,
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO wishlist_items (id,wishlist_id,variant_id) VALUES (:id,:wishlist,:variant)"
                    ),
                    {"id": uuid4(), "wishlist": wishlist, "variant": variant},
                )
            command.upgrade(config, "head")
            rows = connection.execute(
                text("SELECT product_id FROM wishlist_items WHERE wishlist_id=:id"),
                {"id": wishlist},
            ).all()
            assert rows == [(product,)]
            command.downgrade(config, "0002")
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM wishlist_items WHERE wishlist_id=:id"),
                    {"id": wishlist},
                )
                == 1
            )
            command.upgrade(config, "head")
            assert (
                connection.scalar(
                    text("SELECT product_id FROM wishlist_items WHERE wishlist_id=:id"),
                    {"id": wishlist},
                )
                == product
            )
        finally:
            transaction.rollback()

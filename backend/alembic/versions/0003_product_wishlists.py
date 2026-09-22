"""Save wishlists at product level, retaining one entry per product."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = depends_on = None


def upgrade():
    op.add_column("wishlist_items", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE wishlist_items w SET product_id = v.product_id FROM product_variants v WHERE w.variant_id = v.id"
    )
    op.execute(
        "DELETE FROM wishlist_items a USING wishlist_items b WHERE a.wishlist_id=b.wishlist_id AND a.product_id=b.product_id AND a.id>b.id"
    )
    op.drop_constraint("uq_wishlist_items_wishlist_id", "wishlist_items", type_="unique")
    op.drop_constraint(
        "fk_wishlist_items_variant_id_product_variants", "wishlist_items", type_="foreignkey"
    )
    op.drop_index("ix_wishlist_items_variant_id", table_name="wishlist_items")
    op.drop_column("wishlist_items", "variant_id")
    op.alter_column("wishlist_items", "product_id", nullable=False)
    op.create_foreign_key(
        "fk_wishlist_items_product_id_products",
        "wishlist_items",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_index("ix_wishlist_items_product_id", "wishlist_items", ["product_id"])
    op.create_unique_constraint(
        "uq_wishlist_items_wishlist_id", "wishlist_items", ["wishlist_id", "product_id"]
    )


def downgrade():
    op.add_column("wishlist_items", sa.Column("variant_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE wishlist_items w SET variant_id=(SELECT v.id FROM product_variants v WHERE v.product_id=w.product_id ORDER BY v.created_at,v.id LIMIT 1)"
    )
    # Products without any variant cannot be represented in the old schema.
    op.execute("DELETE FROM wishlist_items WHERE variant_id IS NULL")
    op.drop_constraint("uq_wishlist_items_wishlist_id", "wishlist_items", type_="unique")
    op.drop_constraint(
        "fk_wishlist_items_product_id_products", "wishlist_items", type_="foreignkey"
    )
    op.drop_index("ix_wishlist_items_product_id", table_name="wishlist_items")
    op.drop_column("wishlist_items", "product_id")
    op.alter_column("wishlist_items", "variant_id", nullable=False)
    op.create_foreign_key(
        "fk_wishlist_items_variant_id_product_variants",
        "wishlist_items",
        "product_variants",
        ["variant_id"],
        ["id"],
    )
    op.create_index("ix_wishlist_items_variant_id", "wishlist_items", ["variant_id"])
    op.create_unique_constraint(
        "uq_wishlist_items_wishlist_id", "wishlist_items", ["wishlist_id", "variant_id"]
    )

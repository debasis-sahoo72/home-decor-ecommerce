"""Catalog metadata, compare prices and public listing indexes."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = depends_on = None


def upgrade():
    for table in ("categories", "products"):
        op.add_column(
            table, sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        op.add_column(table, sa.Column("seo_title", sa.String(70)))
        op.add_column(table, sa.Column("seo_description", sa.String(160)))
    op.add_column(
        "categories", sa.Column("description", sa.Text(), server_default="", nullable=False)
    )
    op.add_column(
        "products", sa.Column("specifications", JSONB(), server_default="{}", nullable=False)
    )
    op.add_column(
        "products", sa.Column("featured", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column("product_variants", sa.Column("compare_at_price", sa.Numeric(12, 2)))
    op.create_check_constraint(
        "compare_price", "product_variants", "compare_at_price IS NULL OR compare_at_price >= price"
    )
    op.create_index(
        "ix_products_public_created",
        "products",
        ["created_at", "id"],
        postgresql_where=sa.text("active AND archived_at IS NULL"),
    )
    op.create_index(
        "ix_variants_active_price",
        "product_variants",
        ["price", "product_id"],
        postgresql_where=sa.text("active"),
    )
    op.execute(
        "CREATE INDEX ix_products_search ON products USING gin (to_tsvector('english', name || ' ' || description))"
    )


def downgrade():
    op.drop_index("ix_products_search", table_name="products")
    op.drop_index("ix_variants_active_price", table_name="product_variants")
    op.drop_index("ix_products_public_created", table_name="products")
    op.drop_constraint(op.f("ck_product_variants_compare_price"), "product_variants", type_="check")
    op.drop_column("product_variants", "compare_at_price")
    op.drop_column("products", "featured")
    op.drop_column("products", "specifications")
    op.drop_column("categories", "description")
    for table in ("categories", "products"):
        for column in ("active", "seo_title", "seo_description"):
            op.drop_column(table, column)

"""Replace manual featured collections with price-based offers."""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = depends_on = None


def upgrade():
    op.drop_column("products", "featured")


def downgrade():
    # The removed editorial flags cannot be recovered; products default to unfeatured.
    op.add_column(
        "products", sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false())
    )

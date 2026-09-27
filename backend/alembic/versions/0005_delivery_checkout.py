"""Urban standard delivery and idempotent checkout metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "delivery_pincodes",
        sa.Column("urban", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # Existing coverage has not been classified: fail closed until explicitly reviewed.
    op.execute(
        "UPDATE delivery_pincodes SET service='standard', min_days=GREATEST(min_days,3), max_days=GREATEST(max_days,5) WHERE service='next_day'"
    )
    op.drop_constraint(op.f("ck_delivery_pincodes_service"), "delivery_pincodes", type_="check")
    op.create_check_constraint(
        op.f("ck_delivery_pincodes_service"), "delivery_pincodes", "service = 'standard'"
    )
    op.add_column("orders", sa.Column("checkout_key", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_orders_checkout_key", "orders", ["checkout_key"])
    op.add_column("orders", sa.Column("quote_hash", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "payments",
        sa.Column("initiation_started", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade():
    op.drop_column("payments", "initiation_started")
    op.drop_column("orders", "expires_at")
    op.drop_column("orders", "quote_hash")
    op.drop_constraint("uq_orders_checkout_key", "orders", type_="unique")
    op.drop_column("orders", "checkout_key")
    op.drop_constraint(op.f("ck_delivery_pincodes_service"), "delivery_pincodes", type_="check")
    op.create_check_constraint(
        op.f("ck_delivery_pincodes_service"),
        "delivery_pincodes",
        "service IN ('next_day','standard')",
    )
    op.drop_column("delivery_pincodes", "urban")

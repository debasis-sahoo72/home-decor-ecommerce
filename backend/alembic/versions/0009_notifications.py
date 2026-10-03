"""Transactional delivery records and customer WhatsApp opt-in."""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("whatsapp_phone", sa.String(16)))
    op.add_column("users", sa.Column("whatsapp_opted_in_at", sa.DateTime(timezone=True)))
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id")),
        sa.Column("event_key", sa.String(150), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(200)),
        sa.Column("error_code", sa.String(40)),
        sa.Column("consent_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("event_key", "channel"),
        sa.CheckConstraint("channel IN ('email','whatsapp')", name="channel"),
        sa.CheckConstraint(
            "status IN ('pending','sending','accepted','failed','unknown','skipped')", name="status"
        ),
    )
    for column in ("user_id", "order_id", "status"):
        op.create_index(f"ix_notifications_{column}", "notifications", [column])


def downgrade():
    op.drop_table("notifications")
    op.drop_column("users", "whatsapp_opted_in_at")
    op.drop_column("users", "whatsapp_phone")

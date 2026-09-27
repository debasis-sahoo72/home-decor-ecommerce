"""Validated media metadata and durable Cloudinary cleanup intents."""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = depends_on = None


def upgrade():
    op.add_column("product_images", sa.Column("cloud_name", sa.String(100)))
    op.add_column("product_images", sa.Column("format", sa.String(10)))
    op.add_column("product_images", sa.Column("byte_size", sa.Integer()))
    op.create_table(
        "media_cleanup",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("cloud_name", sa.String(100), nullable=False),
        sa.Column("public_id", sa.String(255), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("cloud_name", "public_id"),
    )
    op.create_index("ix_media_cleanup_not_before", "media_cleanup", ["not_before"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM media_cleanup")):
        raise RuntimeError(
            "Drain media cleanup before downgrading; pending assets must not be abandoned."
        )
    op.drop_table("media_cleanup")
    for name in ("byte_size", "format", "cloud_name"):
        op.drop_column("product_images", name)

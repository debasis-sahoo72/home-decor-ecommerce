"""Customer address metadata and one default per owner."""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = depends_on = None


def upgrade():
    op.add_column("addresses", sa.Column("landmark", sa.String(200), nullable=True))
    op.add_column(
        "addresses", sa.Column("country", sa.String(2), server_default="IN", nullable=False)
    )
    op.add_column(
        "addresses",
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute(
        "UPDATE addresses SET is_default=true WHERE id IN (SELECT DISTINCT ON (user_id) id FROM addresses ORDER BY user_id,created_at,id)"
    )
    op.create_check_constraint(op.f("ck_addresses_country"), "addresses", "country = 'IN'")
    op.create_index(
        "uq_addresses_default_user",
        "addresses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade():
    op.drop_index("uq_addresses_default_user", table_name="addresses")
    op.drop_constraint(op.f("ck_addresses_country"), "addresses", type_="check")
    op.drop_column("addresses", "is_default")
    op.drop_column("addresses", "country")
    op.drop_column("addresses", "landmark")

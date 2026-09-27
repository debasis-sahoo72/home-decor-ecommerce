"""Fulfilment state machine; existing payment and snapshot conventions stay intact."""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = depends_on = None

OLD = "'awaiting_payment','paid','processing','shipped','delivered','cancelled'"
NEW = OLD + ",'packed','out_for_delivery','return_requested','returned','refunded'"
GRAPH = """
 (OLD.status='awaiting_payment' AND NEW.status IN ('paid','cancelled')) OR
 (OLD.status='paid' AND NEW.status IN ('processing','cancelled')) OR
 (OLD.status='processing' AND NEW.status IN ('packed','cancelled')) OR
 (OLD.status='packed' AND NEW.status IN ('shipped','cancelled')) OR
 (OLD.status='shipped' AND NEW.status='out_for_delivery') OR
 (OLD.status='out_for_delivery' AND NEW.status='delivered') OR
 (OLD.status='delivered' AND NEW.status='return_requested') OR
 (OLD.status='return_requested' AND NEW.status IN ('returned','delivered')) OR
 (OLD.status IN ('returned','cancelled') AND NEW.status='refunded')
"""


def install(graph):
    op.execute(
        """CREATE OR REPLACE FUNCTION audit_orders() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP = 'INSERT' THEN
   IF NEW.status <> 'awaiting_payment' THEN RAISE EXCEPTION 'Invalid initial status'; END IF;
 ELSE
   IF ROW(NEW.subtotal,NEW.shipping_fee,NEW.tax,NEW.discount,NEW.total,NEW.currency,NEW.shipping_snapshot,NEW.delivery_snapshot)
     IS DISTINCT FROM ROW(OLD.subtotal,OLD.shipping_fee,OLD.tax,OLD.discount,OLD.total,OLD.currency,OLD.shipping_snapshot,OLD.delivery_snapshot)
     THEN RAISE EXCEPTION 'Order snapshots are immutable'; END IF;
   IF NEW.status = OLD.status THEN RETURN NEW; END IF;
   IF NOT ("""
        + graph
        + """) THEN RAISE EXCEPTION 'Invalid status transition'; END IF;
 END IF;
 INSERT INTO order_status_events(id,order_id,from_status,to_status,actor,reason,created_at)
 VALUES(gen_random_uuid(),NEW.id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,NEW.status,
 coalesce(nullif(current_setting('app.actor',true),''),session_user),
 coalesce(nullif(current_setting('app.reason',true),''),'state transition'),clock_timestamp());
 RETURN NEW;
END $$"""
    )


def upgrade():
    op.drop_constraint(op.f("ck_orders_status"), "orders", type_="check")
    op.create_check_constraint(op.f("ck_orders_status"), "orders", f"status IN ({NEW})")
    install(GRAPH)
    op.create_index("ix_orders_owner_created", "orders", ["user_id", "created_at", "id"])
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"])


def downgrade():
    if op.get_bind().scalar(sa.text(f"SELECT count(*) FROM orders WHERE status NOT IN ({OLD})")):
        raise RuntimeError(
            "Cannot downgrade while extended order states are in use; no data was changed."
        )
    install("""(OLD.status='awaiting_payment' AND NEW.status IN ('paid','cancelled')) OR
      (OLD.status='paid' AND NEW.status IN ('processing','cancelled')) OR
      (OLD.status='processing' AND NEW.status IN ('shipped','cancelled')) OR
      (OLD.status='shipped' AND NEW.status='delivered')""")
    op.drop_index("ix_orders_status_created", table_name="orders")
    op.drop_index("ix_orders_owner_created", table_name="orders")
    op.drop_constraint(op.f("ck_orders_status"), "orders", type_="check")
    op.create_check_constraint(op.f("ck_orders_status"), "orders", f"status IN ({OLD})")

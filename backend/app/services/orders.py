from datetime import datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.entities import Inventory, Order, OrderStatusEvent, Payment, User
from app.services import addresses, checkout
from app.services.delivery import INDIA
from app.services.shopping import money

STATUSES = {
    "PENDING_PAYMENT": "awaiting_payment",
    "CONFIRMED": "paid",
    "PROCESSING": "processing",
    "PACKED": "packed",
    "SHIPPED": "shipped",
    "OUT_FOR_DELIVERY": "out_for_delivery",
    "DELIVERED": "delivered",
    "CANCELLED": "cancelled",
    "RETURN_REQUESTED": "return_requested",
    "RETURNED": "returned",
    "REFUNDED": "refunded",
}
PUBLIC = {v: k for k, v in STATUSES.items()}
TRANSITIONS = {
    "awaiting_payment": {"paid", "cancelled"},
    "paid": {"processing", "cancelled"},
    "processing": {"packed", "cancelled"},
    "packed": {"shipped", "cancelled"},
    "shipped": {"out_for_delivery"},
    "out_for_delivery": {"delivered"},
    "delivered": {"return_requested"},
    "return_requested": {"returned", "delivered"},
    "returned": {"refunded"},
    "cancelled": {"refunded"},
    "refunded": set(),
}


def validate_transition(source, target):
    if target not in TRANSITIONS.get(source, set()):
        raise AppError(409, "invalid_transition", "That order status transition is not allowed.")


def page(db, query, page_number, size, render):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.offset((page_number - 1) * size).limit(size)).unique().all()
    return dict(
        items=[render(row) for row in rows],
        page=page_number,
        total=total,
        pages=(total + size - 1) // size,
    )


def brief(order):
    return dict(
        id=str(order.id),
        number=order.number,
        status=PUBLIC[order.status],
        total=money(order.total),
        currency=order.currency,
        created_at=order.created_at.isoformat(),
        item_count=sum(i.quantity for i in order.items),
    )


def listing(db, user_id=None, status=None, q="", date_from=None, date_to=None, page_number=1):
    query = select(Order).options(selectinload(Order.items))
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
    if status:
        query = query.where(Order.status == STATUSES[status])
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.outerjoin(User).where(
            or_(
                Order.number.ilike(f"%{escaped}%", escape="\\"),
                User.email.ilike(f"%{escaped}%", escape="\\"),
                User.name.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    if date_from:
        query = query.where(Order.created_at >= datetime.combine(date_from, time.min, INDIA))
    if date_to:
        query = query.where(
            Order.created_at < datetime.combine(date_to + timedelta(days=1), time.min, INDIA)
        )
    return page(
        db, query.order_by(Order.created_at.desc(), Order.id.desc()), page_number, 24, brief
    )


def get(db, order_id, user_id=None):
    query = select(Order).where(Order.id == order_id)
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
    order = db.scalar(query)
    if order is None:
        raise AppError(404, "order_not_found", "Order not found.")
    return order


def detail(db, order, admin=False):
    result = brief(order)
    events = db.scalars(
        select(OrderStatusEvent)
        .where(OrderStatusEvent.order_id == order.id)
        .order_by(OrderStatusEvent.created_at, OrderStatusEvent.id)
    ).all()
    result.update(
        subtotal=money(order.subtotal),
        discount=money(order.discount),
        tax=money(order.tax),
        shipping_fee=money(order.shipping_fee),
        address=order.shipping_snapshot,
        delivery=order.delivery_snapshot.get("quote", order.delivery_snapshot),
        items=[
            dict(
                name=i.name,
                sku=i.sku,
                quantity=i.quantity,
                unit_price=money(i.unit_price),
                total=money(i.quantity * i.unit_price),
            )
            for i in order.items
        ],
        history=[
            dict(
                status=PUBLIC.get(e.to_status, e.to_status),
                created_at=e.created_at.isoformat(),
                **({"actor": e.actor, "reason": e.reason} if admin else {}),
            )
            for e in events
        ],
    )
    if admin:
        user = db.get(User, order.user_id) if order.user_id else None
        result["customer"] = (
            dict(id=str(user.id), name=user.name, email=user.email) if user else None
        )
        result["allowed_transitions"] = [
            PUBLIC[s] for s in sorted(TRANSITIONS[order.status] - {"paid", "refunded"})
        ]
        result["payments"] = [
            dict(status=p.status, amount=money(p.amount), refunded_amount=money(p.refunded_amount))
            for p in order.payments
        ]
    return result


def transition(db, order_id, expected, target, reason, actor):
    order = get(db, order_id)
    if order.user_id:
        addresses.lock_owner(db, order.user_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order.status != STATUSES[expected]:
        raise AppError(409, "stale_order", "The order changed. Refresh before updating its status.")
    target = STATUSES[target]
    validate_transition(order.status, target)
    if target == "paid":
        raise AppError(
            409,
            "payment_verification_required",
            "Confirmation requires verified payment; administrators cannot mark an order paid.",
        )
    if target == "refunded":
        # Refunds must be provider-verified, never manually asserted by an admin.
        raise AppError(
            409,
            "refund_verification_required",
            "Refund confirmation will be handled by the payment integration.",
        )
    if target == "cancelled":
        payments = list(
            db.scalars(select(Payment).where(Payment.order_id == order.id).with_for_update())
        )
        if order.status == "awaiting_payment":
            if any(p.initiation_started or p.provider_order_id for p in payments):
                raise AppError(
                    409,
                    "payment_in_progress",
                    "Reconcile the started payment before cancelling this order.",
                )
            if order.checkout_key:
                checkout.release(db, order, reason, actor="admin:" + str(actor))
                db.commit()
                return detail(db, order, admin=True)
        elif order.checkout_key:
            for item in sorted(order.items, key=lambda i: str(i.variant_id)):
                if item.variant_id:
                    stock = db.scalar(
                        select(Inventory)
                        .where(Inventory.variant_id == item.variant_id)
                        .with_for_update()
                    )
                    if stock:
                        stock.on_hand += item.quantity
    checkout.audit(db, "admin:" + str(actor), reason)
    order.status = target
    db.commit()
    return detail(db, order, admin=True)

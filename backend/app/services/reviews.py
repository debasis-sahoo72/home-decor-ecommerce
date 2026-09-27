from sqlalchemy import select

from app.core.errors import AppError
from app.models.entities import Order, OrderItem, OrderStatusEvent, ProductVariant, Review
from app.services.addresses import lock_owner
from app.services.catalog import detail


def eligibility(db, user, product_id):
    detail(db, product_id)
    existing = db.scalar(
        select(Review).where(Review.user_id == user.id, Review.product_id == product_id)
    )
    # Delivery history preserves eligibility even when a received item is returned.
    received = db.scalar(
        select(Order.id)
        .join(OrderItem)
        .join(ProductVariant)
        .where(
            Order.user_id == user.id,
            ProductVariant.product_id == product_id,
            select(OrderStatusEvent.order_id)
            .where(
                OrderStatusEvent.order_id == Order.id,
                OrderStatusEvent.to_status == "delivered",
            )
            .exists(),
        )
        .limit(1)
    )
    return dict(
        eligible=user.role == "customer" and received is not None and existing is None,
        review=dict(
            id=str(existing.id), status=existing.status, rating=existing.rating, body=existing.body
        )
        if existing
        else None,
    )


def create(db, user, product_id, data):
    # Serialize submissions by the same customer; the unique constraint is a second guard.
    lock_owner(db, user.id)
    state = eligibility(db, user, product_id)
    if state["review"]:
        raise AppError(409, "review_exists", "You have already reviewed this product.")
    if not state["eligible"]:
        raise AppError(403, "review_ineligible", "You can review this product after delivery.")
    row = Review(
        user_id=user.id, product_id=product_id, rating=data.rating, body=data.body, status="pending"
    )
    db.add(row)
    db.commit()
    return dict(id=str(row.id), status=row.status, rating=row.rating, body=row.body)

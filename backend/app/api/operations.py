from datetime import date, datetime, time, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.checkout import CheckoutInput, provider
from app.api.dependencies import current_user, require_admin, session_csrf
from app.core.errors import AppError
from app.db import get_session
from app.models.entities import (
    DeliveryPincode,
    Inventory,
    Order,
    Payment,
    PaymentStatusEvent,
    Product,
    ProductVariant,
    Review,
    User,
)
from app.services import catalog, checkout, orders
from app.services.delivery import INDIA
from app.services.shopping import money

customer = APIRouter(
    prefix="/orders", tags=["customer orders"], dependencies=[Depends(current_user)]
)
admin = APIRouter(prefix="/admin", tags=["admin operations"], dependencies=[Depends(require_admin)])
Status = Literal[
    "PENDING_PAYMENT",
    "CONFIRMED",
    "PROCESSING",
    "PACKED",
    "SHIPPED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
    "RETURN_REQUESTED",
    "RETURNED",
    "REFUNDED",
]


@customer.post("", status_code=201, dependencies=[Depends(session_csrf)])
def create_order(
    data: CheckoutInput,
    user=Depends(current_user),
    db: Session = Depends(get_session),
    gateway=Depends(provider),
):
    result = checkout.create(
        db,
        user.id,
        data.address_id,
        data.idempotency_key,
        data.quote_hash,
        gateway,
        require_payment=False,
    )
    return orders.detail(db, orders.get(db, UUID(result["id"]), user.id))


@customer.get("")
def my_orders(
    status: Status | None = None,
    page: int = Query(1, ge=1, le=10000),
    user=Depends(current_user),
    db: Session = Depends(get_session),
):
    return orders.listing(db, user_id=user.id, status=status, page_number=page)


@customer.get("/{order_id}")
def my_order(order_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    return orders.detail(db, orders.get(db, order_id, user.id))


@admin.get("/orders")
def all_orders(
    status: Status | None = None,
    q: str = Query("", max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1, le=10000),
    db: Session = Depends(get_session),
):
    if date_from and date_to and date_from > date_to:
        raise AppError(422, "date_range", "Start date must precede end date.")
    return orders.listing(
        db, status=status, q=q, date_from=date_from, date_to=date_to, page_number=page
    )


@admin.get("/orders/{order_id}")
def all_order(order_id: UUID, db: Session = Depends(get_session)):
    return orders.detail(db, orders.get(db, order_id), admin=True)


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_status: Status
    status: Status
    reason: str = Field(min_length=3, max_length=300)


@admin.patch("/orders/{order_id}/status", dependencies=[Depends(session_csrf)])
def update_status(
    order_id: UUID,
    data: Transition,
    actor=Depends(require_admin),
    db: Session = Depends(get_session),
):
    return orders.transition(db, order_id, data.expected_status, data.status, data.reason, actor.id)


@admin.get("/dashboard")
def dashboard(db: Session = Depends(get_session)):
    today = datetime.now(INDIA).date()
    start, end = (
        datetime.combine(today, time.min, INDIA),
        datetime.combine(today + timedelta(days=1), time.min, INDIA),
    )
    count = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.created_at >= start, Order.created_at < end)
    )
    captured = select(PaymentStatusEvent.payment_id).where(
        PaymentStatusEvent.to_status == "captured",
        PaymentStatusEvent.created_at >= start,
        PaymentStatusEvent.created_at < end,
    )
    revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.id.in_(captured))
    )
    pending = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.status.in_(["awaiting_payment", "paid", "processing", "packed"]))
    )
    low = db.scalar(
        select(func.count(func.distinct(Product.id)))
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .where(
            Product.active.is_(True),
            Product.archived_at.is_(None),
            ProductVariant.active.is_(True),
            Inventory.on_hand - Inventory.reserved <= 5,
        )
    )
    return dict(
        date=today.isoformat(),
        timezone="Asia/Kolkata",
        orders_today=count,
        revenue_today=money(revenue),
        pending_orders=pending,
        low_stock_products=low,
        low_stock_threshold=5,
    )


@admin.get("/inventory")
def inventory(
    q: str = Query("", max_length=100),
    low_only: bool = False,
    page: int = Query(1, ge=1, le=10000),
    db: Session = Depends(get_session),
):
    query = (
        select(ProductVariant)
        .join(Product)
        .join(Inventory)
        .options(selectinload(ProductVariant.product), selectinload(ProductVariant.inventory))
    )
    if q:
        query = query.where(
            or_(
                Product.name.icontains(q, autoescape=True),
                ProductVariant.sku.icontains(q, autoescape=True),
            )
        )
    if low_only:
        query = query.where(Inventory.on_hand - Inventory.reserved <= 5)
    return orders.page(
        db,
        query.order_by(ProductVariant.sku, ProductVariant.id),
        page,
        24,
        lambda v: dict(
            id=str(v.id),
            name=v.product.name,
            sku=v.sku,
            active=v.active,
            on_hand=v.inventory.on_hand,
            reserved=v.inventory.reserved,
            available=v.inventory.on_hand - v.inventory.reserved,
        ),
    )


@admin.get("/customers")
def customers(
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=10000),
    db: Session = Depends(get_session),
):
    query = select(User).where(User.role == "customer")
    if q:
        query = query.where(
            or_(User.name.icontains(q, autoescape=True), User.email.icontains(q, autoescape=True))
        )
    return orders.page(
        db,
        query.order_by(User.created_at.desc(), User.id),
        page,
        24,
        lambda u: dict(
            id=str(u.id),
            name=u.name,
            email=u.email,
            status=u.status,
            created_at=u.created_at.isoformat(),
        ),
    )


@admin.get("/delivery")
def delivery(
    q: str = Query("", max_length=6, pattern=r"^[0-9]*$"),
    page: int = Query(1, ge=1, le=10000),
    db: Session = Depends(get_session),
):
    query = select(DeliveryPincode).where(DeliveryPincode.pincode.startswith(q))
    return orders.page(
        db,
        query.order_by(DeliveryPincode.pincode),
        page,
        24,
        lambda d: dict(
            pincode=d.pincode,
            service=d.service,
            urban=d.urban,
            active=d.active,
            min_days=d.min_days,
            max_days=d.max_days,
            cutoff_hour=d.cutoff_hour,
            fee=money(d.fee),
        ),
    )


@admin.get("/reviews")
def reviews(
    status: Literal["pending", "published", "rejected"] | None = None,
    page: int = Query(1, ge=1, le=10000),
    db: Session = Depends(get_session),
):
    query = select(Review)
    if status:
        query = query.where(Review.status == status)
    return orders.page(
        db,
        query.order_by(Review.created_at.desc(), Review.id),
        page,
        24,
        lambda r: dict(
            id=str(r.id),
            product_id=str(r.product_id),
            product_name=db.get(Product, r.product_id).name,
            rating=r.rating,
            body=r.body,
            status=r.status,
            created_at=r.created_at.isoformat(),
        ),
    )


class Moderation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pending", "published", "rejected"]


@admin.patch("/reviews/{review_id}", dependencies=[Depends(session_csrf)])
def moderate(review_id: UUID, data: Moderation, db: Session = Depends(get_session)):
    review = catalog.get_record(db, Review, review_id)
    review.status = data.status
    db.commit()
    return {"id": str(review.id), "status": review.status}


@admin.get("/catalog")
def products(
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=10000),
    db: Session = Depends(get_session),
):
    query = select(Product).options(
        selectinload(Product.category),
        selectinload(Product.images),
        selectinload(Product.variants).selectinload(ProductVariant.inventory),
    )
    if q:
        query = query.where(
            or_(
                Product.name.icontains(q, autoescape=True),
                Product.slug.icontains(q, autoescape=True),
            )
        )
    return orders.page(
        db,
        query.order_by(Product.created_at.desc(), Product.id),
        page,
        24,
        lambda p: catalog.product_view(p, admin=True),
    )

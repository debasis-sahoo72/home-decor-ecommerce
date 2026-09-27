from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Record:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Record, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('customer','admin')", name="role"),
        CheckConstraint("status IN ('active','disabled')", name="status"),
        CheckConstraint("email = lower(trim(email))", name="normalized_email"),
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(20), default="customer", server_default="customer")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    addresses: Mapped[list["Address"]] = relationship(back_populates="user")


class Address(Record, Base):
    __tablename__ = "addresses"
    __table_args__ = (
        CheckConstraint("pincode ~ '^[0-9]{6}$'", name="pincode"),
        CheckConstraint("country = 'IN'", name="country"),
        Index(
            "uq_addresses_default_user", "user_id", unique=True, postgresql_where=text("is_default")
        ),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    landmark: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2), server_default="IN", default="IN")
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    recipient: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    line1: Mapped[str] = mapped_column(String(200))
    line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    pincode: Mapped[str] = mapped_column(String(6))
    user: Mapped[User] = relationship(back_populates="addresses")


class Category(Record, Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(160))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Record, Base):
    __tablename__ = "products"
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    specifications: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(160))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    category: Mapped[Category] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product")


class ProductImage(Record, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "position"),
        CheckConstraint("position >= 0 AND width > 0 AND height > 0", name="dimensions"),
        CheckConstraint("url LIKE 'https://%'", name="https"),
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    public_id: Mapped[str] = mapped_column(String(255), unique=True)
    url: Mapped[str] = mapped_column(String(2048))
    alt: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    cloud_name: Mapped[str | None] = mapped_column(String(100))
    format: Mapped[str | None] = mapped_column(String(10))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    product: Mapped[Product] = relationship(back_populates="images")


class MediaCleanup(Record, Base):
    """Durable cleanup intent; no image bytes or credentials are stored."""
    __tablename__ = "media_cleanup"
    __table_args__ = (UniqueConstraint("cloud_name", "public_id"),)
    cloud_name: Mapped[str] = mapped_column(String(100))
    public_id: Mapped[str] = mapped_column(String(255))
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ProductVariant(Record, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price"),
        CheckConstraint(
            "compare_at_price IS NULL OR compare_at_price >= price", name="compare_price"
        ),
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    product: Mapped[Product] = relationship(back_populates="variants")
    inventory: Mapped["Inventory"] = relationship(back_populates="variant", uselist=False)


class Inventory(Record, Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand", name="stock"),
    )
    variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id"), unique=True)
    on_hand: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reserved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    variant: Mapped[ProductVariant] = relationship(back_populates="inventory")


class Cart(Record, Base):
    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint("(user_id IS NOT NULL) <> (guest_token_hash IS NOT NULL)", name="owner"),
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    guest_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)


class CartItem(Record, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id"),
        CheckConstraint("quantity > 0 AND quantity <= 100", name="quantity"),
    )
    cart_id: Mapped[UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)


class Wishlist(Record, Base):
    __tablename__ = "wishlists"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)


class WishlistItem(Record, Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("wishlist_id", "product_id"),)
    wishlist_id: Mapped[UUID] = mapped_column(
        ForeignKey("wishlists.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)


class Order(Record, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_payment','paid','processing','packed','shipped','out_for_delivery','delivered','cancelled','return_requested','returned','refunded')",
            name="status",
        ),
        CheckConstraint(
            "subtotal >= 0 AND shipping_fee >= 0 AND tax >= 0 AND discount >= 0 AND total >= 0 AND total = subtotal + shipping_fee + tax - discount",
            name="totals",
        ),
        CheckConstraint("currency = 'INR'", name="currency"),
    )
    number: Mapped[str] = mapped_column(String(40), unique=True)
    checkout_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    quote_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="awaiting_payment", server_default="awaiting_payment", index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    shipping_snapshot: Mapped[dict] = mapped_column(JSONB)
    delivery_snapshot: Mapped[dict] = mapped_column(JSONB)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderItem(Record, Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0 AND unit_price >= 0", name="values"),)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), index=True
    )
    sku: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Record, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "(status = 'refunded' AND refunded_amount = amount) OR (status = 'partially_refunded' AND refunded_amount > 0 AND refunded_amount < amount) OR (status NOT IN ('refunded','partially_refunded') AND refunded_amount = 0)",
            name="refund_status",
        ),
        CheckConstraint(
            "status IN ('created','authorized','captured','failed','partially_refunded','refunded')",
            name="status",
        ),
        CheckConstraint(
            "amount > 0 AND refunded_amount >= 0 AND refunded_amount <= amount", name="amount"
        ),
        CheckConstraint("currency = 'INR'", name="currency"),
    )
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    initiation_started: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[str] = mapped_column(
        String(30), default="created", server_default="created", index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    order: Mapped[Order] = relationship(back_populates="payments")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    actor: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentStatusEvent(Base):
    __tablename__ = "payment_status_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    actor: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(300))
    provider_event_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeliveryPincode(Record, Base):
    __tablename__ = "delivery_pincodes"
    __table_args__ = (
        CheckConstraint("pincode ~ '^[0-9]{6}$'", name="pincode"),
        CheckConstraint("service = 'standard'", name="service"),
        CheckConstraint(
            "min_days >= 1 AND max_days >= min_days AND fee >= 0 AND cutoff_hour BETWEEN 0 AND 23",
            name="delivery",
        ),
    )
    pincode: Mapped[str] = mapped_column(String(6), unique=True)
    service: Mapped[str] = mapped_column(String(20))
    min_days: Mapped[int] = mapped_column(Integer)
    max_days: Mapped[int] = mapped_column(Integer)
    cutoff_hour: Mapped[int] = mapped_column(Integer, default=12)
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    urban: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Review(Record, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating"),
        CheckConstraint("status IN ('pending','published','rejected')", name="status"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")


class AuthSession(Record, Base):
    __tablename__ = "sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthRateBucket(Base):
    __tablename__ = "auth_rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


Index("ix_orders_owner_created", Order.user_id, Order.created_at, Order.id)
Index("ix_orders_status_created", Order.status, Order.created_at)
Index(
    "ix_products_public_created",
    Product.created_at,
    Product.id,
    postgresql_where=text("active AND archived_at IS NULL"),
)
Index(
    "ix_variants_active_price",
    ProductVariant.price,
    ProductVariant.product_id,
    postgresql_where=text("active"),
)
Index(
    "ix_products_search",
    text("to_tsvector('english'::regconfig, (name::text || ' '::text) || description)"),
    _table=Product.__table__,
    postgresql_using="gin",
)

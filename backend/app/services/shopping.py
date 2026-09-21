"""Product-page purchase checks; carts do not reserve inventory."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import AppError
from app.models.entities import (
    Cart,
    CartItem,
    Category,
    DeliveryPincode,
    Inventory,
    Product,
    ProductVariant,
    Review,
    User,
)
from app.services.catalog import detail


def available_variant(db, variant_id, quantity):
    # Lock product/category status as well as stock for a consistent purchase check.
    variant = db.scalar(
        select(ProductVariant)
        .join(Product)
        .join(Category)
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.active.is_(True),
            Product.active.is_(True),
            Product.archived_at.is_(None),
            Category.active.is_(True),
            Category.archived_at.is_(None),
        )
        .with_for_update()
    )
    if variant is None:
        raise AppError(404, "unavailable", "This option is no longer available.")
    stock = db.scalar(select(Inventory).where(Inventory.variant_id == variant_id).with_for_update())
    if stock is None or stock.on_hand - stock.reserved < quantity:
        raise AppError(
            409,
            "insufficient_stock",
            "There is not enough stock for this quantity. Please choose fewer items.",
        )
    return variant


def add_item(db, token_hash, variant_id, quantity):
    # Lock the cart first, then the variant: repeat clicks are serialized.
    db.execute(
        insert(Cart)
        .values(guest_token_hash=token_hash)
        .on_conflict_do_nothing(index_elements=[Cart.guest_token_hash])
    )
    cart = db.scalar(select(Cart).where(Cart.guest_token_hash == token_hash).with_for_update())
    item = db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id)
    )
    total = quantity + (item.quantity if item else 0)
    if total > 100:
        raise AppError(422, "quantity_limit", "A maximum of 100 of each option can be added.")
    count = db.scalar(select(func.count()).select_from(CartItem).where(CartItem.cart_id == cart.id))
    if item is None and count >= 100:
        raise AppError(422, "cart_limit", "Your bag can hold up to 100 different options.")
    available_variant(db, variant_id, total)
    if item:
        item.quantity = total
    else:
        db.add(CartItem(cart_id=cart.id, variant_id=variant_id, quantity=quantity))
    db.commit()
    return {
        "quantity": total,
        "message": "Added to your bag. Stock is checked again before ordering.",
    }


def cart_items(db, token_hash):
    cart = db.scalar(select(Cart).where(Cart.guest_token_hash == token_hash))
    if cart is None:
        return {"items": []}
    result = []
    for item in db.scalars(
        select(CartItem)
        .where(CartItem.cart_id == cart.id)
        .order_by(CartItem.created_at, CartItem.id)
    ):
        v = db.get(ProductVariant, item.variant_id)
        p, c = v.product, v.product.category
        stock = v.inventory
        available = stock.on_hand - stock.reserved if stock else 0
        result.append(
            dict(
                id=str(item.id),
                variant_id=str(v.id),
                name=p.name,
                slug=p.slug,
                label=v.label,
                quantity=item.quantity,
                price=str(v.price),
                subtotal=str(v.price * item.quantity),
                available_stock=available,
                available=v.active
                and p.active
                and c.active
                and p.archived_at is None
                and c.archived_at is None
                and available >= item.quantity,
            )
        )
    return {"items": result}


def remove_item(db, token_hash, item_id):
    if not token_hash:
        raise AppError(404, "not_found", "Bag item not found.")
    item = db.scalar(
        select(CartItem)
        .join(Cart)
        .where(Cart.guest_token_hash == token_hash, CartItem.id == item_id)
        .with_for_update()
    )
    if item is None:
        raise AppError(404, "not_found", "Bag item not found.")
    db.delete(item)
    db.commit()


def delivery(db, pincode, now=None):
    rule = db.scalar(
        select(DeliveryPincode).where(
            DeliveryPincode.pincode == pincode, DeliveryPincode.active.is_(True)
        )
    )
    if rule is None:
        return {
            "pincode": pincode,
            "serviceable": False,
            "message": "Delivery is not currently available to this PIN code.",
        }
    india = timezone(timedelta(hours=5, minutes=30))
    local = (now or datetime.now(india)).astimezone(india)
    offset = 1 if local.hour >= rule.cutoff_hour else 0
    return dict(
        pincode=pincode,
        serviceable=True,
        fee=str(rule.fee),
        earliest=(local.date() + timedelta(days=rule.min_days + offset)).isoformat(),
        latest=(local.date() + timedelta(days=rule.max_days + offset)).isoformat(),
        message="Estimated delivery, subject to stock and confirmation at checkout.",
    )


def purchase_preview(db, variant_id, quantity, pincode):
    variant = available_variant(db, variant_id, quantity)
    quote = delivery(db, pincode)
    if not quote["serviceable"]:
        raise AppError(422, "not_serviceable", quote["message"])
    result = dict(
        variant_id=str(variant.id),
        name=variant.product.name,
        slug=variant.product.slug,
        label=variant.label,
        sku=variant.sku,
        quantity=quantity,
        price=str(variant.price),
        subtotal=str(variant.price * quantity),
        delivery=quote,
        message="Purchase review only. No order has been placed and no stock has been reserved.",
    )
    db.rollback()  # Release read locks; actual order creation must check and reserve again.
    return result


def reviews(db, product_id: UUID, page: int):
    detail(db, product_id)  # Apply identical visibility rules to reviews and products.
    conditions = (Review.product_id == product_id, Review.status == "published")
    total = db.scalar(select(func.count()).select_from(Review).where(*conditions))
    rows = db.execute(
        select(Review, User.name)
        .join(User)
        .where(*conditions)
        .order_by(Review.created_at.desc(), Review.id)
        .offset((page - 1) * 10)
        .limit(10)
    )
    return dict(
        items=[
            dict(
                id=str(r.id),
                rating=r.rating,
                body=r.body,
                author=name.split()[0] if name.split() else "Customer",
                created_at=r.created_at.isoformat(),
            )
            for r, name in rows
        ],
        page=page,
        pages=(total + 9) // 10,
        total=total,
    )

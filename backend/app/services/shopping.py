"""Product-page purchase checks; carts do not reserve inventory."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
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


def owner_cart(db, token_hash=None, user_id=None, create=False, lock=False):
    if user_id is None and token_hash is None:
        return None
    key = "user_id" if user_id else "guest_token_hash"
    value = user_id or token_hash
    if create:
        db.execute(
            insert(Cart)
            .values(**{key: value})
            .on_conflict_do_nothing(index_elements=[getattr(Cart, key)])
        )
    query = select(Cart).where(getattr(Cart, key) == value)
    return db.scalar(query.with_for_update() if lock else query)


def add_item(db, token_hash, variant_id, quantity, user_id=None):
    cart = owner_cart(db, token_hash, user_id, create=True, lock=True)
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


def money(value):
    return str(Decimal(value).quantize(Decimal("0.01")))


def cart_items(db, token_hash=None, user_id=None, pincode=None):
    cart = owner_cart(db, token_hash, user_id)
    result = []
    retail = Decimal("0")
    merchandise = Decimal("0")
    rows = (
        db.scalars(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.created_at, CartItem.id)
        )
        if cart
        else []
    )
    for item in rows:
        v = db.get(ProductVariant, item.variant_id)
        p, c = v.product, v.product.category
        stock = v.inventory
        available = max(0, stock.on_hand - stock.reserved) if stock else 0
        visible = (
            v.active and p.active and c.active and p.archived_at is None and c.archived_at is None
        )
        line = v.price * item.quantity
        original = (v.compare_at_price or v.price) * item.quantity
        merchandise += line
        retail += original
        image = min(p.images, key=lambda i: i.position) if p.images else None
        result.append(
            dict(
                id=str(item.id),
                variant_id=str(v.id),
                product_id=str(p.id),
                name=p.name,
                slug=p.slug,
                label=v.label,
                sku=v.sku,
                quantity=item.quantity,
                price=money(v.price),
                compare_at_price=money(v.compare_at_price) if v.compare_at_price else None,
                subtotal=money(line),
                discount=money(original - line),
                available_stock=available if visible else 0,
                available=bool(visible and available >= item.quantity),
                image={"url": image.url, "alt": image.alt} if image else None,
            )
        )
    quote = delivery(db, pincode) if pincode else None
    valid = bool(result) and all(i["available"] for i in result)
    fee = Decimal(quote["fee"]) if quote and quote["serviceable"] and valid else None
    return dict(
        items=result,
        owner="account" if user_id else "guest",
        item_count=sum(i["quantity"] for i in result),
        subtotal=money(retail),
        discount=money(retail - merchandise),
        merchandise_total=money(merchandise),
        delivery=quote,
        delivery_fee=money(fee) if fee is not None else None,
        total=money(merchandise + fee) if fee is not None else None,
        stock_valid=valid,
        currency="INR",
    )


def owned_item(db, token_hash, item_id, user_id=None):
    cart = owner_cart(db, token_hash, user_id, lock=True)
    item = (
        db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.id == item_id))
        if cart
        else None
    )
    if item is None:
        raise AppError(404, "not_found", "Bag item not found.")
    return item


def update_item(db, token_hash, item_id, quantity, user_id=None):
    item = owned_item(db, token_hash, item_id, user_id)
    available_variant(db, item.variant_id, quantity)
    item.quantity = quantity
    db.commit()


def remove_item(db, token_hash, item_id, user_id=None):
    db.delete(owned_item(db, token_hash, item_id, user_id))
    db.commit()


def clear_cart(db, token_hash, user_id=None):
    cart = owner_cart(db, token_hash, user_id, lock=True)
    if cart:
        db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    db.commit()


def merge_guest_cart(db, token_hash, user_id):
    if not token_hash:
        return
    guest = owner_cart(db, token_hash)
    if guest is None:
        return
    account = owner_cart(db, user_id=user_id, create=True)
    # All cart mutations lock their parent; merging locks both in stable ID order.
    list(
        db.scalars(
            select(Cart)
            .where(Cart.id.in_([guest.id, account.id]))
            .order_by(Cart.id)
            .with_for_update()
        )
    )
    rows = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.cart_id.in_([guest.id, account.id]))
            .order_by(CartItem.variant_id)
        )
    )
    existing = {i.variant_id: i for i in rows if i.cart_id == account.id}
    incoming = [i for i in rows if i.cart_id == guest.id]
    if len(set(existing) | {i.variant_id for i in incoming}) > 100:
        raise AppError(
            409,
            "cart_limit",
            "Your combined bag exceeds 100 options. Clear some guest items before signing in.",
        )
    for item in incoming:
        target = existing.get(item.variant_id)
        if target:
            target.quantity = min(100, target.quantity + item.quantity)
            db.delete(item)
        else:
            item.cart_id = account.id
            target = item
        # Preserve unavailable entries for review; never silently discard a saved item.
        variant = db.get(ProductVariant, item.variant_id)
        inventory = db.scalar(
            select(Inventory).where(Inventory.variant_id == variant.id).with_for_update()
        )
        remaining = inventory.on_hand - inventory.reserved if inventory else 0
        if remaining > 0:
            target.quantity = min(target.quantity, remaining)
    db.flush()
    db.delete(guest)
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

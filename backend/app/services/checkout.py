"""Atomic checkout snapshots, inventory reservations and verified payment settlement."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text

from app.core.errors import AppError
from app.models.entities import (
    CartItem,
    Inventory,
    Order,
    OrderItem,
    Payment,
)
from app.services import addresses, shopping
from app.services.delivery import estimated_window


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def audit(db, actor, reason):
    # Database triggers append exactly one event per transition.
    db.execute(
        text(
            "SELECT set_config('app.actor', :actor, true), set_config('app.reason', :reason, true)"
        ),
        {"actor": actor, "reason": reason},
    )


def quote(db, user_id, address_id):
    addresses.lock_owner(db, user_id)
    address = addresses.owned(db, user_id, address_id)
    cart = shopping.owner_cart(db, user_id=user_id, lock=True)
    if cart is None:
        raise AppError(422, "empty_cart", "Your bag is empty.")
    items = list(
        db.scalars(
            select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.variant_id)
        )
    )
    if not items:
        raise AppError(422, "empty_cart", "Your bag is empty.")
    for item in items:
        shopping.available_variant(db, item.variant_id, item.quantity)
    cart_view = shopping.cart_items(db, user_id=user_id, pincode=address.pincode)
    if not cart_view["delivery"]["serviceable"]:
        raise AppError(422, "not_serviceable", cart_view["delivery"]["message"])
    shipping = addresses.view(address)
    shipping["id"] = str(shipping["id"])
    result = dict(cart=cart_view, address=shipping)
    # Hash only purchasable facts, not fluctuating available-stock counts.
    result["quote_hash"] = fingerprint(
        dict(
            address=shipping,
            delivery=cart_view["delivery"],
            items=[
                {k: i[k] for k in ("id", "variant_id", "quantity", "price", "compare_at_price")}
                for i in cart_view["items"]
            ],
        )
    )
    return result


def owned(db, user_id, order_id):
    addresses.lock_owner(db, user_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id, Order.checkout_key.is_not(None))
        .with_for_update()
    )
    if order is None:
        raise AppError(404, "order_not_found", "Order not found.")
    return order


def payment_for(db, order):
    return db.scalar(select(Payment).where(Payment.order_id == order.id).with_for_update())


def view(db, order):
    payment = payment_for(db, order)
    delivery = dict(order.delivery_snapshot["quote"])
    delivery.update(
        estimated_window(
            delivery["min_days"],
            delivery["max_days"],
            delivery["cutoff_hour"],
            payment.updated_at if payment.status == "captured" else None,
        )
    )
    return dict(
        id=str(order.id),
        number=order.number,
        status=order.status,
        subtotal=shopping.money(order.subtotal),
        discount=shopping.money(order.discount),
        delivery_fee=shopping.money(order.shipping_fee),
        total=shopping.money(order.total),
        currency=order.currency,
        address=order.shipping_snapshot,
        delivery=delivery,
        items=[
            dict(name=i.name, sku=i.sku, quantity=i.quantity, price=shopping.money(i.unit_price))
            for i in order.items
        ],
        can_cancel=order.status == "awaiting_payment" and not payment.initiation_started,
        payment_started=payment.initiation_started,
        provider_order_id=payment.provider_order_id,
        expires_at=order.expires_at.isoformat() if order.expires_at else None,
    )


def release(db, order, reason, actor="checkout"):
    from app.services import notifications
    for item in sorted(order.items, key=lambda i: str(i.variant_id)):
        stock = db.scalar(
            select(Inventory).where(Inventory.variant_id == item.variant_id).with_for_update()
        )
        stock.reserved -= item.quantity
    audit(db, actor, reason)
    order.status = "cancelled"
    db.flush()
    notifications.order_event(db, order)


def pending(db, user_id):
    addresses.lock_owner(db, user_id)
    rows = list(
        db.scalars(
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.status == "awaiting_payment",
                Order.checkout_key.is_not(None),
            )
            .order_by(Order.created_at)
            .with_for_update()
        )
    )
    for order in rows:
        payment = payment_for(db, order)
        if order.expires_at <= datetime.now(timezone.utc) and not payment.initiation_started:
            release(db, order, "Unstarted checkout expired after 30 minutes")
        else:
            return order
    return None


def create(db, user_id, address_id, key, quote_hash, provider, require_payment=True):
    addresses.lock_owner(db, user_id)
    scoped_key = fingerprint([str(user_id), str(key)])
    existing = db.scalar(select(Order).where(Order.checkout_key == scoped_key))
    if existing:
        if existing.quote_hash != quote_hash or existing.shipping_snapshot["id"] != str(address_id):
            raise AppError(
                409,
                "idempotency_conflict",
                "This checkout request was already used. Review your bag again.",
            )
        return view(db, existing)
    active = pending(db, user_id)
    if active:
        raise AppError(
            409,
            "pending_checkout",
            "Resume or cancel your existing checkout before starting another.",
        )
    if require_payment and not provider.enabled:
        raise AppError(
            503, "payment_unavailable", "Online payment is not available yet. Your bag is saved."
        )
    result = quote(db, user_id, address_id)
    if quote_hash != result["quote_hash"]:
        raise AppError(
            409,
            "quote_changed",
            "Your bag, address or delivery price changed. Review the latest totals before paying.",
        )
    cart = result["cart"]
    if Decimal(cart["total"]) < 1:
        raise AppError(422, "payment_minimum", "Online orders must total at least ₹1.")
    order = Order(
        number="YS-" + uuid4().hex[:24].upper(),
        user_id=user_id,
        checkout_key=scoped_key,
        quote_hash=quote_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        subtotal=Decimal(cart["subtotal"]),
        discount=Decimal(cart["discount"]),
        shipping_fee=Decimal(cart["delivery_fee"]),
        tax=0,
        total=Decimal(cart["total"]),
        shipping_snapshot=result["address"],
        delivery_snapshot=dict(
            quote=cart["delivery"],
            cart_items=[dict(id=i["id"], quantity=i["quantity"]) for i in cart["items"]],
        ),
    )
    audit(db, "checkout", "Server-priced checkout; inventory reserved")
    db.add(order)
    db.flush()
    for item in sorted(cart["items"], key=lambda i: i["variant_id"]):
        stock = db.scalar(
            select(Inventory).where(Inventory.variant_id == item["variant_id"]).with_for_update()
        )
        stock.reserved += item["quantity"]
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=item["variant_id"],
                name=item["name"],
                sku=item["sku"],
                quantity=item["quantity"],
                unit_price=Decimal(item["price"]),
            )
        )
    payment = Payment(order_id=order.id, idempotency_key=scoped_key, amount=order.total)
    db.add(payment)
    db.flush()
    db.commit()
    from app.services import notifications

    notifications.dispatch(db)
    return view(db, order)


def initiate(db, user_id, order_id, provider):
    order = owned(db, user_id, order_id)
    payment = payment_for(db, order)
    if order.status != "awaiting_payment":
        raise AppError(409, "order_state", "This order is no longer awaiting payment.")
    if not payment.initiation_started and order.expires_at <= datetime.now(timezone.utc):
        release(db, order, "Checkout expired before payment")
        db.commit()
        from app.services import notifications

        notifications.dispatch(db)
        raise AppError(409, "checkout_expired", "Checkout expired. Review your bag again.")
    if not provider.enabled:
        raise AppError(503, "payment_unavailable", "Payment is temporarily unavailable.")
    if not payment.provider_order_id:
        if payment.initiation_started:
            raise AppError(
                409,
                "payment_pending",
                "Payment setup needs reconciliation. Please contact support with your order number; do not start another payment.",
            )
        # Persist intent BEFORE the external call: an ambiguous timeout must never create a second provider order.
        payment.initiation_started = True
        db.commit()
        remote = provider.create(order)
        order = owned(db, user_id, order_id)
        payment = payment_for(db, order)
        if (
            remote.get("amount") != int(order.total * 100)
            or remote.get("currency") != "INR"
            or not remote.get("id", "").startswith("order_")
        ):
            raise AppError(
                502, "provider_mismatch", "Payment setup needs review. Please contact support."
            )
        payment.provider_order_id = remote["id"]
        db.commit()
    return dict(
        key=provider.key,
        order_id=payment.provider_order_id,
        amount=int(order.total * 100),
        currency="INR",
    )


def confirm(db, user_id, order_id, provider):
    order = owned(db, user_id, order_id)
    if order.status != "awaiting_payment":
        return view(db, order)
    payment = payment_for(db, order)
    if not payment.provider_order_id:
        return view(db, order)
    captured = provider.captured(payment.provider_order_id)
    if captured is None:
        return view(db, order)
    if (
        captured.get("order_id") != payment.provider_order_id
        or captured.get("currency") != "INR"
        or captured.get("amount") != int(order.total * 100)
        or captured.get("status") != "captured"
        or not captured.get("id", "").startswith("pay_")
        or captured.get("amount_refunded", 0) != 0
    ):
        raise AppError(
            409, "payment_mismatch", "Payment details require review. Please contact support."
        )
    cart = shopping.owner_cart(db, user_id=user_id, lock=True)
    for item in sorted(order.items, key=lambda i: str(i.variant_id)):
        stock = db.scalar(
            select(Inventory).where(Inventory.variant_id == item.variant_id).with_for_update()
        )
        stock.reserved -= item.quantity
        stock.on_hand -= item.quantity
    if cart:
        for original in order.delivery_snapshot["cart_items"]:
            entry = db.scalar(
                select(CartItem).where(CartItem.id == original["id"], CartItem.cart_id == cart.id)
            )
            if entry:
                if entry.quantity <= original["quantity"]:
                    db.delete(entry)
                else:
                    entry.quantity -= original["quantity"]
    audit(
        db,
        "razorpay-verification",
        "Captured payment fetched and matched server-side; inventory consumed",
    )
    payment.provider_payment_id = captured["id"]
    payment.status = "captured"
    order.status = "paid"
    from app.services import notifications

    notifications.order_event(db, order)
    db.commit()
    notifications.dispatch(db)
    return view(db, order)


def cancel(db, user_id, order_id):
    order = owned(db, user_id, order_id)
    if order.status == "cancelled":
        return view(db, order)
    if order.status != "awaiting_payment" or payment_for(db, order).initiation_started:
        raise AppError(
            409,
            "payment_started",
            "Payment has started. Check its status before contacting support to cancel.",
        )
    release(db, order, "Customer cancelled before payment initiation")
    db.commit()
    from app.services import notifications

    notifications.dispatch(db)
    return view(db, order)

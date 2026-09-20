from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models.entities import (
    Category,
    Inventory,
    Order,
    OrderItem,
    OrderStatusEvent,
    Payment,
    PaymentStatusEvent,
    Product,
    ProductVariant,
)


def variant(db):
    category = Category(name="Test", slug=str(uuid4()))
    db.add(category)
    db.flush()
    product = Product(category_id=category.id, name="Test", slug=str(uuid4()), description="Test")
    db.add(product)
    db.flush()
    row = ProductVariant(
        product_id=product.id, sku=str(uuid4()), label="Standard", price=Decimal("1299.95")
    )
    db.add(row)
    db.commit()
    return row


def order(db):
    row = Order(
        number=str(uuid4()),
        subtotal=Decimal("1299.95"),
        total=Decimal("1299.95"),
        shipping_snapshot={"pincode": "560001"},
        delivery_snapshot={"service": "standard"},
    )
    db.add(row)
    db.commit()
    return row


def test_decimal_round_trip_and_inventory_constraint(db):
    row = variant(db)
    db.expire_all()
    assert db.get(ProductVariant, row.id).price == Decimal("1299.95")
    db.add(Inventory(variant_id=row.id, on_hand=1, reserved=2))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_foreign_key_and_positive_quantity(db):
    row = order(db)
    db.add(
        OrderItem(
            order_id=row.id,
            variant_id=uuid4(),
            sku="missing",
            name="Missing",
            quantity=1,
            unit_price=Decimal("1.00"),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(
        OrderItem(
            order_id=row.id, sku="invalid", name="Invalid", quantity=0, unit_price=Decimal("1.00")
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_order_audit_transitions_and_append_only_history(db):
    row = order(db)
    db.execute(text("SELECT set_config('app.actor','test-admin',true)"))
    db.execute(text("SELECT set_config('app.reason','verified test payment',true)"))
    row.status = "paid"
    db.commit()
    events = db.scalars(select(OrderStatusEvent).where(OrderStatusEvent.order_id == row.id)).all()
    assert len(events) == 2
    assert any(x.to_status == "paid" and x.actor == "test-admin" for x in events)
    row.status = "awaiting_payment"
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()
    db.delete(events[0])
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_order_snapshot_cannot_be_rewritten(db):
    row = order(db)
    row.shipping_snapshot = {"pincode": "999999"}
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_order_item_snapshot_cannot_be_rewritten(db):
    row = order(db)
    item = OrderItem(
        order_id=row.id, sku="test", name="Test", quantity=1, unit_price=Decimal("1299.95")
    )
    db.add(item)
    db.commit()
    item.quantity = 2
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_refund_state_requires_matching_amount(db):
    row = order(db)
    payment = Payment(order_id=row.id, amount=Decimal("100.00"), idempotency_key=str(uuid4()))
    db.add(payment)
    db.commit()
    payment.status = "captured"
    db.commit()
    payment.status = "refunded"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    payment.status = "refunded"
    payment.refunded_amount = Decimal("100.00")
    db.commit()


def test_payment_audit_and_invalid_initial_state(db):
    row = order(db)
    payment = Payment(order_id=row.id, amount=Decimal("1299.95"), idempotency_key=str(uuid4()))
    db.add(payment)
    db.commit()
    payment.status = "captured"
    db.commit()
    assert (
        len(
            db.scalars(
                select(PaymentStatusEvent).where(PaymentStatusEvent.payment_id == payment.id)
            ).all()
        )
        == 2
    )
    payment.status = "failed"
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()
    db.add(
        Payment(
            order_id=row.id, amount=Decimal("1.00"), idempotency_key=str(uuid4()), status="captured"
        )
    )
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()

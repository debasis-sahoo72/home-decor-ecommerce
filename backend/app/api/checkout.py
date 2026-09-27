import hashlib
import hmac
import json
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_admin, session_csrf
from app.core.errors import AppError
from app.db import get_session
from app.models.entities import DeliveryPincode, Order, Payment
from app.services import checkout
from app.services.payment_provider import Razorpay

router = APIRouter(tags=["checkout"])


def provider(request: Request):
    return Razorpay(request.app.state.settings)


class QuoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address_id: UUID


class CheckoutInput(QuoteInput):
    idempotency_key: UUID
    quote_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.get("/checkout/config")
def config(gateway=Depends(provider)):
    return {"payment_available": gateway.enabled}


@router.post("/checkout/quote", dependencies=[Depends(session_csrf)])
def quote(data: QuoteInput, user=Depends(current_user), db: Session = Depends(get_session)):
    result = checkout.quote(db, user.id, data.address_id)
    db.rollback()
    return result


@router.get("/checkout/pending")
def pending(user=Depends(current_user), db: Session = Depends(get_session)):
    order = checkout.pending(db, user.id)
    result = checkout.view(db, order) if order else None
    db.commit()
    return result


@router.post("/checkout/orders", dependencies=[Depends(session_csrf)], status_code=201)
def create(
    data: CheckoutInput,
    user=Depends(current_user),
    db: Session = Depends(get_session),
    gateway=Depends(provider),
):
    return checkout.create(
        db, user.id, data.address_id, data.idempotency_key, data.quote_hash, gateway
    )


@router.get("/checkout/orders/{order_id}")
def detail(order_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    return checkout.view(db, checkout.owned(db, user.id, order_id))


@router.post("/checkout/orders/{order_id}/payment", dependencies=[Depends(session_csrf)])
def initiate(
    order_id: UUID,
    user=Depends(current_user),
    db: Session = Depends(get_session),
    gateway=Depends(provider),
):
    return checkout.initiate(db, user.id, order_id, gateway)


@router.post("/checkout/orders/{order_id}/confirm", dependencies=[Depends(session_csrf)])
def confirm(
    order_id: UUID,
    user=Depends(current_user),
    db: Session = Depends(get_session),
    gateway=Depends(provider),
):
    return checkout.confirm(db, user.id, order_id, gateway)


@router.post("/checkout/orders/{order_id}/cancel", dependencies=[Depends(session_csrf)])
def cancel(order_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    return checkout.cancel(db, user.id, order_id)


@router.post("/payments/razorpay/webhook")
async def webhook(request: Request, db: Session = Depends(get_session), gateway=Depends(provider)):
    secret = request.app.state.settings.razorpay_webhook_secret.get_secret_value()
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(expected, signature):
        raise AppError(400, "invalid_signature", "Invalid webhook signature.")
    try:
        event = json.loads(body)
        remote = event["payload"]["payment"]["entity"]
        remote_id = remote["order_id"]
        if not isinstance(remote_id, str):
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        return {"received": True}
    payment = db.scalar(select(Payment).where(Payment.provider_order_id == remote_id))
    if payment:
        order = db.get(Order, payment.order_id)
        if order.user_id:
            checkout.confirm(db, order.user_id, order.id, gateway)
    return {"received": True}


class DeliveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: Literal["standard"] = "standard"
    urban: bool = False
    active: bool = False
    min_days: int = Field(ge=2, le=60, strict=True)
    max_days: int = Field(ge=2, le=60, strict=True)
    cutoff_hour: int = Field(default=12, ge=0, le=23, strict=True)
    fee: Decimal = Field(ge=0, le=10000, max_digits=7, decimal_places=2)

    @model_validator(mode="after")
    def valid_window(self):
        if self.max_days < self.min_days:
            raise ValueError("Delivery maximum must be at least the minimum")
        if self.active and not self.urban:
            raise ValueError("Only explicitly verified urban PIN codes can be enabled")
        return self


@router.put("/admin/delivery/{pincode}", dependencies=[Depends(session_csrf)])
def save_delivery(
    pincode: str,
    data: DeliveryInput,
    user=Depends(require_admin),
    db: Session = Depends(get_session),
):
    import re

    if not re.fullmatch(r"[1-9][0-9]{5}", pincode):
        raise AppError(422, "invalid_pincode", "Enter a valid six-digit Indian PIN code.")
    # Serialize admin upserts, including inserts for a previously unknown PIN.
    from sqlalchemy.dialects.postgresql import insert

    from app.services.addresses import lock_owner

    lock_owner(db, user.id)
    values = data.model_dump()
    db.execute(
        insert(DeliveryPincode)
        .values(pincode=pincode, **values)
        .on_conflict_do_update(index_elements=[DeliveryPincode.pincode], set_=values)
    )
    db.commit()
    return {"pincode": pincode, **values}

"""Transactional delivery receipts; inline dispatch, no external queue.

Stage in the business transaction, then dispatch only after its commit. A future
worker can call deliver() on pending IDs without changing event producers.
"""

import logging
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.models.entities import Notification, Order, Payment, User

logger = logging.getLogger("decor.notifications")
MESSAGES = {
    "registration": (
        "Welcome to Your Sanctuary",
        "Your account is ready. Sign in to manage your orders.",
    ),
    "order_confirmed": ("Order confirmed", "Your order is confirmed."),
    "payment_confirmed": ("Payment confirmed", "Your payment has been verified."),
    "shipped": ("Order shipped", "Your order has been shipped."),
    "delivered": ("Order delivered", "Your order has been marked delivered."),
    "cancelled": (
        "Order cancelled",
        "Your order has been cancelled. This message does not confirm a refund.",
    ),
    "refunded": (
        "Refund confirmed",
        "Your refund has been verified. Your bank may take time to display it.",
    ),
}


def settings_for(db):
    return db.info.get("settings") or get_settings()


def stage(db, user_id, event, order=None):
    if not user_id or event not in MESSAGES:
        return
    settings = settings_for(db)
    user = db.get(User, user_id)
    if not user or user.status != "active":
        return
    key = f"{order.id if order else user_id}:{event}"
    for channel, enabled in [
        ("email", settings.email_notifications_enabled),
        ("whatsapp", settings.whatsapp_notifications_enabled),
    ]:
        if not enabled or (channel == "whatsapp" and not user.whatsapp_opted_in_at):
            continue
        identifier = db.scalar(
            insert(Notification)
            .values(
                id=uuid4(),
                user_id=user_id,
                order_id=order.id if order else None,
                event_key=key,
                event=event,
                channel=channel,
                status="pending",
                attempts=0,
                consent_at=user.whatsapp_opted_in_at if channel == "whatsapp" else None,
            )
            .on_conflict_do_nothing(index_elements=["event_key", "channel"])
            .returning(Notification.id)
        )
        if identifier:
            db.info.setdefault("notification_ids", []).append(identifier)


def order_event(db, order):
    if order.status == "paid":
        stage(db, order.user_id, "order_confirmed", order)
        stage(db, order.user_id, "payment_confirmed", order)
    elif order.status in {"shipped", "delivered", "cancelled"}:
        stage(db, order.user_id, order.status, order)
    # Refund messages must be staged by a future provider-verified refund flow,
    # not an admin-supplied order status.


def verified_refund_event(db, payment_id):
    """Call within a future verified-refund transaction; never from client success data."""
    payment = db.get(Payment, payment_id)
    if not payment or payment.status != "refunded" or payment.refunded_amount != payment.amount:
        raise ValueError("A recorded full refund is required")
    order = db.get(Order, payment.order_id)
    stage(db, order.user_id, "refunded", order)


class ProviderFailure(Exception):
    def __init__(self, code, uncertain=False):
        self.code, self.uncertain = code, uncertain


class Providers:
    def __init__(self, settings):
        self.settings = settings

    def send(self, row, user, order):
        s = self.settings
        subject, body = MESSAGES[row.event]
        reference = order.number if order else "Your Sanctuary account"
        # Plain text, no addresses, item list, totals, tokens or payment details.
        if row.channel == "email":
            if not s.resend_api_key.get_secret_value() or not s.notification_from_email:
                raise ProviderFailure("not_configured")
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {s.resend_api_key.get_secret_value()}",
                "Idempotency-Key": str(row.id),
            }
            payload = {
                "from": s.notification_from_email,
                "to": [user.email],
                "subject": f"Your Sanctuary — {subject}",
                "text": f"{body}\nReference: {reference}\nSign in to your account for details.",
            }
        else:
            template = s.whatsapp_templates.get(row.event)
            if not all(
                [
                    s.whatsapp_access_token.get_secret_value(),
                    s.whatsapp_phone_number_id,
                    s.whatsapp_api_version,
                    template,
                ]
            ):
                raise ProviderFailure("not_configured")
            url = f"https://graph.facebook.com/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages"
            headers = {"Authorization": f"Bearer {s.whatsapp_access_token.get_secret_value()}"}
            payload = {
                "messaging_product": "whatsapp",
                "to": user.whatsapp_phone.lstrip("+"),
                "type": "template",
                "template": {
                    "name": template,
                    "language": {"code": s.whatsapp_template_language},
                    "components": [
                        {"type": "body", "parameters": [{"type": "text", "text": reference}]}
                    ],
                },
            }
        try:
            with httpx.Client(timeout=5, follow_redirects=False) as client:
                response = client.post(url, headers=headers, json=payload)
            if not response.is_success:
                raise ProviderFailure(
                    f"http_{response.status_code}", uncertain=response.status_code >= 500
                )
            data = response.json()
            identifier = (
                data.get("id")
                if row.channel == "email"
                else data.get("messages", [{}])[0].get("id")
            )
            if not isinstance(identifier, str) or not identifier or len(identifier) > 200:
                raise ProviderFailure("invalid_response", uncertain=True)
            return identifier
        except (httpx.HTTPError, ValueError, IndexError, TypeError):
            raise ProviderFailure("transport_or_response", uncertain=True) from None


def deliver(db, identifier, provider=None):
    row = db.scalar(select(Notification).where(Notification.id == identifier).with_for_update())
    if row is None or row.status not in {"pending", "failed"} or row.attempts >= 3:
        db.rollback()
        return
    settings = settings_for(db)
    user = db.get(User, row.user_id)
    enabled = (
        settings.email_notifications_enabled
        if row.channel == "email"
        else settings.whatsapp_notifications_enabled
    )
    if (
        not enabled
        or not user
        or user.status != "active"
        or (
            row.channel == "whatsapp"
            and (
                not user.whatsapp_phone
                or not user.whatsapp_opted_in_at
                or user.whatsapp_opted_in_at != row.consent_at
            )
        )
    ):
        row.status = "skipped"
        db.commit()
        return
    order = db.get(Order, row.order_id) if row.order_id else None
    row.status = "sending"
    row.attempts += 1
    db.commit()  # Claim before network I/O. A crashed/uncertain send is never blindly replayed.
    try:
        row.provider_id = (provider or Providers(settings)).send(row, user, order)
        row.status, row.error_code = "accepted", None
    except ProviderFailure as error:
        row.status = "unknown" if error.uncertain else "failed"
        row.error_code = error.code
    except Exception:
        row.status, row.error_code = "unknown", "unexpected_provider_error"
    db.commit()


def dispatch(db):
    for identifier in db.info.pop("notification_ids", []):
        try:
            deliver(db, identifier)
        except Exception:
            db.rollback()
            logger.warning("notification_dispatch_failed id=%s", identifier)

"""Local PIN allowlist provider; replace quote() with a carrier adapter in future."""

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.errors import AppError
from app.models.entities import DeliveryPincode

INDIA = timezone(timedelta(hours=5, minutes=30))


def estimated_window(min_days, max_days, cutoff_hour, now=None):
    local = (now or datetime.now(INDIA)).astimezone(INDIA)
    offset = int(local.hour >= cutoff_hour)
    return dict(
        earliest=(local.date() + timedelta(days=min_days + offset)).isoformat(),
        latest=(local.date() + timedelta(days=max_days + offset)).isoformat(),
    )


def quote(db, pincode, now=None):
    if not re.fullmatch(r"[1-9][0-9]{5}", pincode):
        raise AppError(422, "invalid_pincode", "Enter a valid six-digit Indian PIN code.")
    rule = db.scalar(
        select(DeliveryPincode).where(
            DeliveryPincode.pincode == pincode,
            DeliveryPincode.active.is_(True),
            DeliveryPincode.urban.is_(True),
        )
    )
    if rule is None:
        return dict(
            pincode=pincode,
            serviceable=False,
            message="Delivery is not currently available to this PIN code.",
        )
    return dict(
        pincode=pincode,
        serviceable=True,
        service="standard",
        fee=f"{rule.fee:.2f}",
        calendar="calendar_days",
        min_days=rule.min_days,
        max_days=rule.max_days,
        cutoff_hour=rule.cutoff_hour,
        **estimated_window(rule.min_days, rule.max_days, rule.cutoff_hour, now),
        message="Standard delivery estimate in calendar days, subject to payment confirmation.",
    )

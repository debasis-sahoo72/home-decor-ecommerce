"""Small server-only Razorpay adapter. Never accept a client-supplied amount/status."""

import base64
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.errors import AppError


class Razorpay:
    def __init__(self, settings):
        self.key = settings.razorpay_key_id
        self.secret = settings.razorpay_key_secret.get_secret_value()
        self.production = settings.app_env == "production"
        self.webhook_configured = bool(settings.razorpay_webhook_secret.get_secret_value())

    @property
    def enabled(self):
        prefix = "rzp_live_" if self.production else "rzp_test_"
        return bool(
            self.key.startswith(prefix)
            and self.secret
            and (not self.production or self.webhook_configured)
        )

    def call(self, path, body=None):
        if not self.enabled:
            raise AppError(
                503,
                "payment_unavailable",
                "Online payment is not available yet. Your bag is saved.",
            )
        credentials = base64.b64encode(f"{self.key}:{self.secret}".encode()).decode()
        request = Request(
            "https://api.razorpay.com/v1/" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": "Basic " + credentials, "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                return json.load(response)
        except (URLError, TimeoutError, ValueError):
            raise AppError(
                503,
                "payment_unavailable",
                "Payment status could not be checked. Please retry; do not pay again.",
            ) from None

    def create(self, order):
        return self.call(
            "orders", {"amount": int(order.total * 100), "currency": "INR", "receipt": order.number}
        )

    def captured(self, provider_id):
        order = self.call("orders/" + provider_id)
        if order.get("status") != "paid":
            return None
        payments = self.call("orders/" + provider_id + "/payments")
        return next((p for p in payments.get("items", []) if p.get("status") == "captured"), None)

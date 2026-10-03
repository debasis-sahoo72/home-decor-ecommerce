import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from test_auth import csrf, login, register
from test_checkout import basket as basket_fixture
from test_checkout import gateway as gateway_fixture
from test_checkout import item as item_fixture
from test_checkout import serviceable as serviceable_fixture
from test_operations import captured, change, promote

from app.config import Settings
from app.models.entities import Notification, Order, User
from app.services import notifications

basket = basket_fixture
gateway = gateway_fixture
item = item_fixture
serviceable = serviceable_fixture


@pytest.fixture
def enabled(client, db, monkeypatch):
    settings = client.app.state.settings
    settings.email_notifications_enabled = True
    settings.whatsapp_notifications_enabled = True
    calls = []

    def send(self, row, user, order):
        calls.append((row.event, row.channel))
        return "provider-test-id"

    monkeypatch.setattr(notifications.Providers, "send", send)
    return calls


def opt_in(client):
    return client.put(
        "/api/v1/account/notifications",
        headers=csrf(client),
        json={
            "whatsapp_enabled": True,
            "whatsapp_phone": "+919876543210",
        },
    )


def test_registration_disabled_by_default(client, db):
    assert register(client).status_code == 201
    assert db.scalar(select(Notification)) is None


def test_registration_email_and_duplicate_guard(client, db, enabled):
    assert register(client).status_code == 201
    assert enabled == [("registration", "email")]
    user = db.scalar(select(User))
    notifications.stage(db, user.id, "registration")
    db.commit()
    notifications.dispatch(db)
    assert len(enabled) == 1
    assert db.scalar(select(Notification)).status == "accepted"
    assert register(client).status_code == 409
    assert len(enabled) == 1


def test_paid_fulfilment_and_no_duplicate_confirmation(client, db, basket, gateway, enabled):
    assert opt_in(client).status_code == 200
    order = captured(client, basket, gateway)
    assert set(enabled) == {
        ("order_confirmed", "email"),
        ("order_confirmed", "whatsapp"),
        ("payment_confirmed", "email"),
        ("payment_confirmed", "whatsapp"),
    }
    notifications.order_event(db, db.get(Order, order["id"]))
    db.commit()
    notifications.dispatch(db)
    assert len(enabled) == 4
    promote(db)
    states = ["CONFIRMED", "PROCESSING", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED"]
    for source, target in zip(states, states[1:]):
        assert change(client, order["id"], source, target).status_code == 200
    assert ("shipped", "email") in enabled
    assert ("delivered", "whatsapp") in enabled
    assert len(enabled) == 8


def test_preferences_auth_validation_ownership_and_optout(client, db):
    path = "/api/v1/account/notifications"
    assert client.get(path).status_code == 401
    register(client)
    login(client)
    assert client.put(path, json={"whatsapp_enabled": False}).status_code == 403
    for payload in [
        dict(whatsapp_enabled=True),
        dict(whatsapp_enabled=True, whatsapp_phone="98765"),
        dict(whatsapp_enabled=False, user_id="other"),
    ]:
        assert client.put(path, headers=csrf(client), json=payload).status_code == 422
    other = User(name="Other", email="preferences@example.com", password_hash="test")
    db.add(other)
    db.commit()
    assert opt_in(client).status_code == 200
    assert other.whatsapp_phone is None
    response = client.get(path)
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["whatsapp_enabled"] is True
    assert (
        client.put(path, headers=csrf(client), json={"whatsapp_enabled": False}).status_code == 200
    )
    assert client.get(path).json()["whatsapp_phone"] is None


def test_failure_never_rolls_back_registration(client, db, enabled, monkeypatch):
    def fail(*args):
        raise notifications.ProviderFailure("http_401")

    monkeypatch.setattr(notifications.Providers, "send", fail)
    assert register(client).status_code == 201
    assert login(client).status_code == 200
    assert db.scalar(select(Notification)).status == "failed"


def test_unknown_send_is_not_replayed_and_logs_no_sensitive_data(
    client, db, enabled, monkeypatch, caplog
):
    def fail(*args):
        raise RuntimeError("secret customer@example.com +919876543210")

    monkeypatch.setattr(notifications.Providers, "send", fail)
    assert register(client).status_code == 201
    row = db.scalar(select(Notification))
    assert row.status == "unknown"
    notifications.deliver(db, row.id)
    assert row.attempts == 1
    assert "secret customer" not in caplog.text
    assert row.error_code == "unexpected_provider_error"


def test_optout_cancels_staged_whatsapp(client, db, enabled):
    register(client)
    login(client)
    opt_in(client)
    user = db.scalar(select(User))
    notifications.stage(db, user.id, "shipped")
    db.commit()
    client.put(
        "/api/v1/account/notifications", headers=csrf(client), json={"whatsapp_enabled": False}
    )
    notifications.dispatch(db)
    row = db.scalar(select(Notification).where(Notification.channel == "whatsapp"))
    assert row.status == "skipped"
    assert ("shipped", "whatsapp") not in enabled


def test_notification_stage_rolls_back_with_transaction(client, db, enabled):
    register(client)
    user = db.scalar(select(User))
    with db.begin_nested() as transaction:
        notifications.stage(db, user.id, "shipped")
        transaction.rollback()
    notifications.dispatch(db)
    assert enabled == [("registration", "email")]


@pytest.mark.parametrize("channel", ["email", "whatsapp"])
def test_provider_payload_is_minimal_and_server_authenticated(monkeypatch, channel):
    settings = Settings(
        resend_api_key="email-secret",
        notification_from_email="Your Sanctuary <orders@example.com>",
        whatsapp_access_token="wa-secret",
        whatsapp_phone_number_id="123",
        whatsapp_api_version="v25.0",
        whatsapp_templates={"shipped": "ys_shipped"},
    )
    original = httpx.Client
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "email-id", "messages": [{"id": "wa-id"}]})

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    row = SimpleNamespace(id="delivery-id", channel=channel, event="shipped")
    user = SimpleNamespace(
        email="customer@example.com", whatsapp_phone="+919876543210", password_hash="NEVER_SEND"
    )
    order = SimpleNamespace(
        number="YS-123", total=Decimal("900"), shipping_snapshot={"address": "NEVER_SEND"}
    )
    notifications.Providers(settings).send(row, user, order)
    request = requests[0]
    payload = json.loads(request.content)
    assert "NEVER_SEND" not in request.content.decode()
    assert request.headers["authorization"].startswith("Bearer ")
    if channel == "email":
        assert request.headers["idempotency-key"] == "delivery-id"
        assert payload["to"] == [user.email]
    else:
        assert payload["type"] == "template"
        assert payload["template"]["components"][0]["parameters"] == [
            {"type": "text", "text": "YS-123"}
        ]


def test_unverified_refund_cannot_be_notified(client, db, basket, gateway, enabled):
    order = captured(client, basket, gateway)
    payment = db.get(Order, order["id"]).payments[0]
    with pytest.raises(ValueError):
        notifications.verified_refund_event(db, payment.id)
    assert not any(event == "refunded" for event, channel in enabled)


def test_cancellation_is_not_a_refund_confirmation(client, db, basket, gateway, enabled):
    from test_checkout import post, submit

    order = submit(client, basket).json()
    assert enabled == []  # No confirmation for an unpaid checkout.
    assert post(client, order, "cancel").status_code == 200
    assert enabled == [("cancelled", "email")]
    assert "does not confirm a refund" in notifications.MESSAGES["cancelled"][1]


def test_verified_full_refund_event_is_deduplicated(client, db, basket, gateway, enabled):
    from app.services.checkout import audit

    order = captured(client, basket, gateway)
    payment = db.get(Order, order["id"]).payments[0]
    audit(db, "test-provider-verification", "Refund verified fixture")
    payment.status = "refunded"
    payment.refunded_amount = payment.amount
    db.flush()
    notifications.verified_refund_event(db, payment.id)
    db.commit()
    notifications.dispatch(db)
    notifications.verified_refund_event(db, payment.id)
    db.commit()
    notifications.dispatch(db)
    assert enabled.count(("refunded", "email")) == 1


@pytest.mark.parametrize(
    "status,uncertain", [(400, False), (401, False), (429, False), (503, True)]
)
def test_provider_rejection_and_uncertain_results(monkeypatch, status, uncertain):
    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(status, json={"error": "sensitive response"})
            ),
            **kwargs,
        ),
    )
    provider = notifications.Providers(
        Settings(resend_api_key="test", notification_from_email="orders@example.com")
    )
    with pytest.raises(notifications.ProviderFailure) as error:
        provider.send(
            SimpleNamespace(id="id", event="registration", channel="email"),
            SimpleNamespace(email="customer@example.com"),
            None,
        )
    assert error.value.uncertain is uncertain
    assert error.value.code == f"http_{status}"


def test_explicit_retry_definite_failure_only(client, db, enabled, monkeypatch):
    def fail(*args):
        raise notifications.ProviderFailure("http_429")

    monkeypatch.setattr(notifications.Providers, "send", fail)
    register(client)
    row = db.scalar(select(Notification))
    assert row.status == "failed"
    provider = SimpleNamespace(send=lambda *args: "accepted-id")
    notifications.deliver(db, row.id, provider)
    assert row.status == "accepted"
    assert row.attempts == 2
    notifications.deliver(db, row.id, provider)
    assert row.attempts == 2

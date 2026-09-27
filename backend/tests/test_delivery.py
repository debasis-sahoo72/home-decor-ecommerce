from datetime import datetime, timezone

import pytest
from test_catalog import admin_headers as admin_fixture
from test_shopping import serviceable as serviceable_fixture

from app.models.entities import DeliveryPincode
from app.services.delivery import quote

serviceable = serviceable_fixture
admin_headers = admin_fixture


def test_bangalore_uses_standard_not_express(client, serviceable):
    data = client.get("/api/v1/delivery/560001").json()
    assert data["service"] == "standard"
    assert data["serviceable"] is True


def test_other_urban_and_rural(db, client):
    db.add(
        DeliveryPincode(
            pincode="400001",
            service="standard",
            urban=True,
            active=True,
            min_days=4,
            max_days=7,
            fee=99,
        )
    )
    db.add(
        DeliveryPincode(
            pincode="400002",
            service="standard",
            urban=False,
            active=True,
            min_days=4,
            max_days=7,
            fee=99,
        )
    )
    db.commit()
    assert client.get("/api/v1/delivery/400001").json()["serviceable"] is True
    assert client.get("/api/v1/delivery/400002").json()["serviceable"] is False
    assert client.get("/api/v1/delivery/999999").json()["serviceable"] is False


@pytest.mark.parametrize("pin", ["000000", "56001", "5600011", "abcdef", "５６０００１"])
def test_invalid_pin(client, pin):
    assert client.get("/api/v1/delivery/" + pin).status_code == 422


def test_calendar_days_include_weekends_and_holidays(db, serviceable):
    # Friday morning -> Monday (3 days), not Wednesday (3 business days).
    result = quote(db, "560001", datetime(2026, 9, 25, 4, tzinfo=timezone.utc))
    assert result["earliest"] == "2026-09-28"
    assert result["calendar"] == "calendar_days"
    holiday = quote(db, "560001", datetime(2026, 12, 22, 4, tzinfo=timezone.utc))
    assert holiday["earliest"] == "2026-12-25"


def test_admin_coverage_validation(client, admin_headers):
    body = dict(min_days=3, max_days=5, fee="50.00", urban=True, active=True)
    path = "/api/v1/admin/delivery/560001"
    assert client.put(path, json=body, headers=admin_headers).status_code == 200
    assert client.get("/api/v1/delivery/560001").json()["service"] == "standard"
    for change in [
        {"service": "next_day"},
        {"urban": False},
        {"fee": "-1"},
        {"min_days": 6},
        {"min_days": 1},
    ]:
        assert client.put(path, json=body | change, headers=admin_headers).status_code == 422

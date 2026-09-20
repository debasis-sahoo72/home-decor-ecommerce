from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import digest, verify_password
from app.models.entities import AuthSession, User

USER = {
    "email": "person@example.com",
    "name": "Test Customer",
    "password": "Warm rooms deserve beautiful light!",
}


def csrf(client):
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def register(client, **changes):
    return client.post("/api/v1/auth/register", json=USER | changes, headers=csrf(client))


def login(client, **changes):
    return client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": USER["password"]} | changes,
        headers=csrf(client),
    )


def test_registration_hash_and_no_secret_response(client, db):
    response = register(client, email="PERSON@EXAMPLE.COM")
    assert response.status_code == 201, response.text
    assert response.json()["email"] == USER["email"]
    assert response.json()["role"] == "customer"
    user = db.scalar(select(User))
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(user.password_hash, USER["password"])
    assert "password" not in response.text


def test_duplicate_registration(client):
    assert register(client).status_code == 201
    response = register(client, email="PERSON@EXAMPLE.COM")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_registered"


def test_login_authorized_and_logout_revokes_session(client, db):
    register(client)
    response = login(client)
    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    token = client.cookies.get("decor-session")
    record = db.scalar(select(AuthSession))
    assert record.token_hash == digest(token) and record.token_hash != token
    assert token not in response.text and "password" not in response.text
    assert client.get("/api/v1/auth/me").status_code == 200
    assert (
        client.post(
            "/api/v1/auth/logout", headers={"X-CSRF-Token": response.json()["csrf_token"]}
        ).status_code
        == 204
    )
    assert db.scalar(select(AuthSession)) is None
    client.cookies.set("decor-session", token)
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize(
    "email,password", [(USER["email"], "wrong password"), ("missing@example.com", USER["password"])]
)
def test_login_failure_is_generic(client, email, password):
    register(client)
    response = login(client, email=email, password=password)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_unauthorized_endpoint(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/admin").status_code == 401


def test_customer_cannot_access_admin(client):
    register(client)
    login(client)
    assert client.get("/api/v1/auth/admin").status_code == 403


def test_admin_endpoint(client, db):
    register(client)
    db.scalar(select(User)).role = "admin"
    db.commit()
    assert login(client).status_code == 200
    assert client.get("/api/v1/auth/admin").status_code == 200


def test_public_registration_cannot_set_admin_role(client):
    assert register(client, role="admin").status_code == 422


@pytest.mark.parametrize("field", ["expires_at", "last_seen_at"])
def test_session_expiry(client, db, field):
    register(client)
    login(client)
    setattr(db.scalar(select(AuthSession)), field, datetime.now(UTC) - timedelta(days=8))
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_disabled_user_login_and_session_rejected(client, db):
    register(client)
    login(client)
    db.scalar(select(User)).status = "disabled"
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.clear()
    assert login(client).status_code == 401


def test_csrf_and_origin_protection(client):
    assert client.post("/api/v1/auth/register", json=USER).status_code == 403
    headers = csrf(client) | {"Origin": "https://evil.example"}
    assert client.post("/api/v1/auth/register", json=USER, headers=headers).status_code == 403
    register(client)
    login(client)
    assert client.post("/api/v1/auth/logout").status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 200


def test_password_validation_no_reflection(client):
    secret = "short"
    response = register(client, password=secret)
    assert response.status_code == 422
    assert secret not in response.text
    assert register(client, password="x" * 129).status_code == 422


def test_rate_limit_persists_failed_attempts(client):
    register(client)
    for _ in range(10):
        assert login(client, password="incorrect").status_code == 401
    response = login(client)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "900"


def test_cors_body_limit_and_cache(client):
    response = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
    assert client.post("/api/v1/auth/login", content=b"x" * 17000).status_code == 413
    response = client.get("/api/v1/auth/me")
    assert response.headers["cache-control"] == "no-store"
    assert "x-request-id" in response.headers


def test_browser_same_origin_get_can_use_referrer(client):
    del client.headers["Origin"]
    response = client.get("/api/v1/auth/csrf", headers={"Referer": "http://127.0.0.1:3000/login"})
    assert response.status_code == 200
    assert client.get("/api/v1/auth/csrf").status_code == 403

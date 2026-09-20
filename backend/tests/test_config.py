import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_development_secrets():
    with pytest.raises(ValidationError):
        Settings(app_env="production", _env_file=None)


def test_wildcard_origins_rejected():
    with pytest.raises(ValidationError):
        Settings(allowed_origins=["*"], _env_file=None)


def test_production_preauth_cookie_flags(client):
    client.app.state.settings = Settings(
        app_env="production",
        auth_secret="a" * 64,
        database_url="postgresql+psycopg://test:secure@localhost/unused",
        allowed_origins=["https://shop.example"],
        _env_file=None,
    )
    with TestClient(
        client.app, base_url="https://shop.example", headers={"Origin": "https://shop.example"}
    ) as secure:
        response = secure.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "__Host-decor-preauth=" in cookie
    assert "HttpOnly" in cookie and "Secure" in cookie and "Path=/" in cookie
    assert "Domain=" not in cookie

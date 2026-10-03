import os

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings
from app.db import get_session
from app.main import create_app


@pytest.fixture(scope="session")
def pg_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("CI", "").lower() in {"true", "1"}:
            pytest.fail("CI requires TEST_DATABASE_URL; database tests must not silently skip")
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database ending in _test")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not parsed.database.endswith("_test"):
        raise ValueError("Integration tests require a PostgreSQL database ending in _test")
    # env.py supports an explicitly supplied connection for tests/migration tooling.
    engine = create_engine(url)
    config = Config("alembic.ini")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(pg_engine):
    with pg_engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(db, pg_engine):
    # Never inherit live media/payment credentials from the developer's .env.
    app = create_app(
        Settings(
            app_env="test",
            auth_ip_limit=100,
            cloudinary_cloud_name="",
            cloudinary_api_key="",
            cloudinary_api_secret="",
            razorpay_key_id="",
            razorpay_key_secret="",
            razorpay_webhook_secret="",
            email_notifications_enabled=False,
            whatsapp_notifications_enabled=False,
        ),
        pg_engine,
    )
    app.dependency_overrides[get_session] = lambda: db
    db.info["settings"] = app.state.settings
    with TestClient(
        app, base_url="http://127.0.0.1:3000", headers={"Origin": "http://127.0.0.1:3000"}
    ) as client:
        yield client

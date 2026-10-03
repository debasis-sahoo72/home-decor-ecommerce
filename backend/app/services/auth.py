import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.errors import AppError
from app.core.security import DUMMY_HASH, digest, hasher, verify_password
from app.models.entities import AuthRateBucket, AuthSession, User
from app.schemas.auth import Credentials, Registration


def throttle(db: Session, settings: Settings, key: str, limit: int) -> None:
    now = datetime.now(UTC)
    hashed = hmac.new(
        settings.auth_secret.get_secret_value().encode(), key.encode(), hashlib.sha256
    ).hexdigest()
    stmt = insert(AuthRateBucket).values(
        key=hashed, count=1, expires_at=now + timedelta(minutes=15)
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[AuthRateBucket.key],
        set_={
            "count": case((AuthRateBucket.expires_at <= now, 1), else_=AuthRateBucket.count + 1),
            "expires_at": case(
                (AuthRateBucket.expires_at <= now, now + timedelta(minutes=15)),
                else_=AuthRateBucket.expires_at,
            ),
        },
    ).returning(AuthRateBucket.count)
    count = db.scalar(stmt)
    db.commit()  # Failed logins must not roll back the rate bucket.
    if count > limit:
        raise AppError(429, "rate_limited", "Too many attempts. Try again in 15 minutes.")


def register(db: Session, data: Registration) -> User:
    from app.services import notifications
    user = User(
        email=str(data.email),
        name=data.name,
        password_hash=hasher.hash(data.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.flush()
        notifications.stage(db, user.id, "registration")
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise AppError(
                409, "email_registered", "An account with this email already exists."
            ) from None
        raise
    notifications.dispatch(db)
    return user


def login(db: Session, settings: Settings, data: Credentials):
    throttle(db, settings, f"login:{data.email}", settings.login_limit)
    user = db.scalar(select(User).where(User.email == str(data.email)))
    valid = verify_password(
        user.password_hash if user else DUMMY_HASH, data.password.get_secret_value()
    )
    if not valid or user is None or user.status != "active":
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(data.password.get_secret_value())
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    hours = settings.admin_session_hours if user.role == "admin" else settings.session_hours
    record = AuthSession(
        user_id=user.id,
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        last_seen_at=now,
        expires_at=now + timedelta(hours=hours),
    )
    db.add(record)
    db.commit()
    return user, token, csrf, hours * 3600


def authenticate(db: Session, settings: Settings, token: str | None):
    if not token or len(token) > 256:
        raise AppError(401, "unauthorized", "Sign in to continue.")
    record = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(token)))
    user = db.get(User, record.user_id) if record else None
    now = datetime.now(UTC)
    idle = settings.admin_idle_minutes if user and user.role == "admin" else settings.idle_minutes
    absolute_hours = (
        settings.admin_session_hours if user and user.role == "admin" else settings.session_hours
    )
    if (
        not record
        or not user
        or user.status != "active"
        or record.expires_at <= now
        or record.created_at + timedelta(hours=absolute_hours) <= now
        or record.last_seen_at + timedelta(minutes=idle) <= now
    ):
        raise AppError(401, "unauthorized", "Sign in to continue.")
    record.last_seen_at = now
    db.commit()
    return user, record


def revoke(db: Session, record: AuthSession) -> None:
    db.execute(delete(AuthSession).where(AuthSession.id == record.id))
    db.commit()

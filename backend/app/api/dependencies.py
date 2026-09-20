import hmac
from urllib.parse import urlsplit

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import digest, valid_preauth
from app.db import get_session
from app.services.auth import authenticate


def require_origin(request: Request):
    origin = request.headers.get("origin")
    if not origin and request.headers.get("referer"):
        try:
            referrer = urlsplit(request.headers["referer"])
            origin = f"{referrer.scheme}://{referrer.netloc}"
        except ValueError:
            origin = None
    if origin not in request.app.state.settings.allowed_origins:
        raise AppError(403, "invalid_origin", "Request origin is not allowed.")


def public_csrf(request: Request):
    require_origin(request)
    settings = request.app.state.settings
    cookie = request.cookies.get(settings.csrf_cookie, "")
    header = request.headers.get("x-csrf-token", "")
    if (
        not cookie
        or len(cookie) > 256
        or len(header) > 256
        or not hmac.compare_digest(cookie.encode(), header.encode())
        or not valid_preauth(cookie, settings.auth_secret.get_secret_value())
    ):
        raise AppError(403, "invalid_csrf", "Refresh the form and try again.")


def current_identity(request: Request, db: Session = Depends(get_session)):
    settings = request.app.state.settings
    return authenticate(db, settings, request.cookies.get(settings.session_cookie))


def current_user(identity=Depends(current_identity)):
    return identity[0]


def require_admin(user=Depends(current_user)):
    if user.role != "admin":
        raise AppError(403, "forbidden", "Administrator access required.")
    return user


def session_csrf(request: Request, identity=Depends(current_identity)):
    require_origin(request)
    header = request.headers.get("x-csrf-token", "")
    if len(header) > 256 or not hmac.compare_digest(digest(header), identity[1].csrf_hash):
        raise AppError(403, "invalid_csrf", "Refresh the form and try again.")
    return identity

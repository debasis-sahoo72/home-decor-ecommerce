import secrets

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import (
    current_user,
    public_csrf,
    require_admin,
    require_origin,
    session_csrf,
)
from app.core.errors import AppError
from app.core.security import digest, preauth_token
from app.db import get_session
from app.schemas.auth import Credentials, CsrfResult, LoginResult, Registration, UserPublic
from app.services import auth

router = APIRouter(prefix="/auth", tags=["authentication"])


def set_cookie(response: Response, request: Request, name: str, value: str, age: int):
    response.set_cookie(
        name,
        value,
        max_age=age,
        httponly=True,
        secure=request.app.state.settings.app_env == "production",
        samesite="lax",
        path="/",
    )


def clear_cookie(response: Response, request: Request, name: str):
    response.delete_cookie(
        name,
        path="/",
        secure=request.app.state.settings.app_env == "production",
        httponly=True,
        samesite="lax",
    )


@router.get("/csrf", response_model=CsrfResult, dependencies=[Depends(require_origin)])
def csrf(request: Request, response: Response, db: Session = Depends(get_session)):
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie)
    if token:
        try:
            _, record = auth.authenticate(db, settings, token)
        except AppError:
            clear_cookie(response, request, settings.session_cookie)
        else:
            csrf_value = secrets.token_urlsafe(32)
            record.csrf_hash = digest(csrf_value)
            db.commit()
            return {"csrf_token": csrf_value}
    value = preauth_token(settings.auth_secret.get_secret_value())
    set_cookie(response, request, settings.csrf_cookie, value, 600)
    return {"csrf_token": value}


def limit_ip(request: Request, db: Session):
    settings = request.app.state.settings
    peer = request.client.host if request.client else "unknown"
    auth.throttle(db, settings, f"auth-ip:{peer}", settings.auth_ip_limit)


@router.post(
    "/register", response_model=UserPublic, status_code=201, dependencies=[Depends(public_csrf)]
)
def register(data: Registration, request: Request, db: Session = Depends(get_session)):
    limit_ip(request, db)
    return auth.register(db, data)


@router.post("/login", response_model=LoginResult, dependencies=[Depends(public_csrf)])
def login(
    data: Credentials, request: Request, response: Response, db: Session = Depends(get_session)
):
    limit_ip(request, db)
    user, token, csrf_value, age = auth.login(db, request.app.state.settings, data)
    set_cookie(response, request, request.app.state.settings.session_cookie, token, age)
    clear_cookie(response, request, request.app.state.settings.csrf_cookie)
    return {"user": user, "csrf_token": csrf_value}


@router.get("/me", response_model=UserPublic)
def me(user=Depends(current_user)):
    return user


@router.get("/admin", response_model=UserPublic)
def admin(user=Depends(require_admin)):
    return user


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    identity=Depends(session_csrf),
    db: Session = Depends(get_session),
):
    auth.revoke(db, identity[1])
    clear_cookie(response, request, request.app.state.settings.session_cookie)

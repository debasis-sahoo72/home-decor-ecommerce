from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import current_identity, public_csrf, session_csrf
from app.core.security import digest, preauth_token, valid_preauth
from app.db import get_session
from app.services import shopping

router = APIRouter(tags=["product shopping"])
AGE = 30 * 24 * 60 * 60


class CartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variant_id: UUID
    quantity: int = Field(ge=1, le=100, strict=True)


class QuantityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1, le=100, strict=True)


class PurchaseInput(CartInput):
    pincode: str = Field(pattern=r"^[0-9]{6}$")


def csrf(request: Request, db: Session = Depends(get_session)):
    if request.cookies.get(request.app.state.settings.session_cookie):
        from app.api.dependencies import current_identity

        session_csrf(request, current_identity(request, db))
    else:
        public_csrf(request)


def cart_token(request, response=None):
    settings = request.app.state.settings
    secret = settings.auth_secret.get_secret_value() + ":cart"
    name = "__Host-decor-cart" if settings.app_env == "production" else "decor-cart"
    token = request.cookies.get(name, "")
    if not token or len(token) > 256 or not valid_preauth(token, secret, max_age=AGE):
        if response is None:
            return None
        token = preauth_token(secret)
        response.set_cookie(
            name,
            token,
            max_age=AGE,
            httponly=True,
            secure=settings.app_env == "production",
            samesite="lax",
            path="/",
        )
    return digest(token)


def owner(request, db, response=None):
    if request.cookies.get(request.app.state.settings.session_cookie):
        return None, current_identity(request, db)[0].id
    return cart_token(request, response), None


@router.get("/cart")
def cart(
    request: Request,
    response: Response,
    pincode: str | None = Query(None, pattern=r"^[0-9]{6}$"),
    db: Session = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    token, user_id = owner(request, db)
    return shopping.cart_items(db, token, user_id, pincode)


@router.post("/cart/items", dependencies=[Depends(csrf)], status_code=201)
def add(data: CartInput, request: Request, response: Response, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    token, user_id = owner(request, db, response)
    return shopping.add_item(db, token, data.variant_id, data.quantity, user_id)


@router.patch("/cart/items/{item_id}", dependencies=[Depends(csrf)], status_code=204)
def update(
    item_id: UUID, data: QuantityInput, request: Request, db: Session = Depends(get_session)
):
    token, user_id = owner(request, db)
    shopping.update_item(db, token, item_id, data.quantity, user_id)
    return Response(status_code=204)


@router.delete("/cart/items/{item_id}", dependencies=[Depends(csrf)], status_code=204)
def remove(item_id: UUID, request: Request, db: Session = Depends(get_session)):
    token, user_id = owner(request, db)
    shopping.remove_item(db, token, item_id, user_id)
    return Response(status_code=204)


@router.delete("/cart", dependencies=[Depends(csrf)], status_code=204)
def clear(request: Request, db: Session = Depends(get_session)):
    token, user_id = owner(request, db)
    shopping.clear_cart(db, token, user_id)
    return Response(status_code=204)


@router.post("/checkout/preview", dependencies=[Depends(csrf)])
def preview(data: PurchaseInput, response: Response, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return shopping.purchase_preview(db, data.variant_id, data.quantity, data.pincode)


@router.get("/delivery/{pincode}")
def delivery(pincode: str, response: Response, db: Session = Depends(get_session)):
    import re

    from app.core.errors import AppError

    if not re.fullmatch(r"[0-9]{6}", pincode):
        raise AppError(422, "invalid_pincode", "Enter a six-digit PIN code.")
    response.headers["Cache-Control"] = "no-store"
    return shopping.delivery(db, pincode)


@router.get("/products/{product_id}/reviews")
def reviews(
    product_id: UUID, page: int = Query(1, ge=1, le=10000), db: Session = Depends(get_session)
):
    return shopping.reviews(db, product_id, page)

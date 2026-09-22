from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, session_csrf
from app.db import get_session
from app.services import wishlist

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


class SavedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID


class MergeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_ids: list[UUID] = Field(max_length=200)


@router.get("")
def listing(response: Response, user=Depends(current_user), db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return wishlist.listing(db, user.id)


@router.post("/items", dependencies=[Depends(session_csrf)])
def add(
    data: SavedInput,
    response: Response,
    user=Depends(current_user),
    db: Session = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    return wishlist.add_products(db, user.id, [data.product_id])


@router.post("/merge", dependencies=[Depends(session_csrf)])
def merge(
    data: MergeInput,
    response: Response,
    user=Depends(current_user),
    db: Session = Depends(get_session),
):
    response.headers["Cache-Control"] = "no-store"
    return wishlist.add_products(db, user.id, data.product_ids, skip_unavailable=True)


@router.delete("/items/{product_id}", status_code=204, dependencies=[Depends(session_csrf)])
def remove(product_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    wishlist.remove(db, user.id, product_id)
    return Response(status_code=204)

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import require_admin, session_csrf
from app.core.errors import AppError
from app.db import get_session
from app.services import media

router = APIRouter(prefix="/admin", tags=["product media"], dependencies=[Depends(require_admin)])


def provider(request: Request):
    return media.Cloudinary(request.app.state.settings)


@router.get("/media/config")
def config(gateway=Depends(provider)):
    return dict(
        enabled=gateway.enabled,
        max_bytes=media.MAX_BYTES,
        max_images=media.MAX_IMAGES,
        formats=["image/jpeg", "image/png", "image/webp"],
    )


@router.get("/products/{product_id}/media")
def list_images(product_id: UUID, db: Session = Depends(get_session)):
    media.lock_product(db, product_id)
    return [media.view(row) for row in media.images(db, product_id)]


@router.post(
    "/products/{product_id}/media/upload", status_code=201, dependencies=[Depends(session_csrf)]
)
async def upload(
    product_id: UUID,
    request: Request,
    alt: str = Query(min_length=1, max_length=300),
    replace_id: UUID | None = None,
    db: Session = Depends(get_session),
    gateway=Depends(provider),
):
    if not alt.strip():
        raise AppError(422, "image_alt", "Describe the product and view shown in this image.")
    data = await request.body()
    return await run_in_threadpool(
        media.upload,
        db,
        product_id,
        data,
        request.headers.get("content-type", "").split(";")[0].lower(),
        alt.strip(),
        gateway,
        replace_id,
    )


class Ordering(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_ids: list[UUID] = Field(max_length=100)


@router.patch("/products/{product_id}/media/order", dependencies=[Depends(session_csrf)])
def reorder(product_id: UUID, data: Ordering, db: Session = Depends(get_session)):
    media.lock_product(db, product_id)
    rows = {r.id: r for r in media.images(db, product_id)}
    if len(data.image_ids) != len(rows) or set(data.image_ids) != set(rows):
        raise AppError(
            409,
            "images_changed",
            "Send every current product image exactly once. Refresh and retry.",
        )
    ordered = [rows[i] for i in data.image_ids]
    media.arrange(db, ordered)
    db.commit()
    return [media.view(row) for row in ordered]


class Caption(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    alt: str = Field(min_length=1, max_length=300)


def owned_image(db, product_id, image_id):
    media.lock_product(db, product_id)
    rows = media.images(db, product_id)
    row = next((r for r in rows if r.id == image_id), None)
    if row is None:
        raise AppError(404, "not_found", "Image not found for this product.")
    return row, rows


@router.patch("/products/{product_id}/media/{image_id}", dependencies=[Depends(session_csrf)])
def caption(product_id: UUID, image_id: UUID, data: Caption, db: Session = Depends(get_session)):
    row, rows = owned_image(db, product_id, image_id)
    row.alt = data.alt
    db.commit()
    return [media.view(row) for row in rows]


@router.delete("/products/{product_id}/media/{image_id}", dependencies=[Depends(session_csrf)])
def remove(product_id: UUID, image_id: UUID, db: Session = Depends(get_session)):
    row, rows = owned_image(db, product_id, image_id)
    media.enqueue(db, row)
    db.delete(row)
    db.flush()
    rows.remove(row)
    media.arrange(db, rows)
    db.commit()
    return [media.view(row) for row in rows]


@router.post("/media/cleanup", dependencies=[Depends(session_csrf)])
def cleanup(db: Session = Depends(get_session), gateway=Depends(provider)):
    return media.cleanup(db, gateway, limit=1)

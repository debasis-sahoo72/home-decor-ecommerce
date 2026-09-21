from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin, session_csrf
from app.core.errors import AppError
from app.db import get_session
from app.models.entities import Category, Inventory, Product, ProductImage, ProductVariant
from app.schemas.catalog import (
    CatalogQuery,
    CategoryWrite,
    ImageWrite,
    ProductWrite,
    StockWrite,
    VariantWrite,
)
from app.services import catalog

router = APIRouter(tags=["catalog"])
admin = [Depends(require_admin), Depends(session_csrf)]


@router.get("/categories")
def categories(db: Session = Depends(get_session)):
    return [
        catalog.category_view(c)
        for c in db.scalars(
            select(Category)
            .where(Category.active.is_(True), Category.archived_at.is_(None))
            .order_by(Category.name, Category.id)
        )
    ]


@router.get("/categories/{slug}")
def category(slug: str, db: Session = Depends(get_session)):
    c = db.scalar(
        select(Category).where(
            Category.slug == slug, Category.active.is_(True), Category.archived_at.is_(None)
        )
    )
    if c is None:
        raise AppError(404, "not_found", "This category is not available.")
    return catalog.category_view(c)


@router.get("/products")
def products(query: Annotated[CatalogQuery, Query()], db: Session = Depends(get_session)):
    return catalog.listing(db, query)


@router.get("/products/slug/{slug}")
def product_slug(slug: str, db: Session = Depends(get_session)):
    return catalog.detail(db, slug, by_slug=True)


@router.get("/products/{product_id}")
def product(product_id: UUID, db: Session = Depends(get_session)):
    return catalog.detail(db, product_id)


@router.get("/admin/categories", dependencies=[Depends(require_admin)])
def admin_categories(db: Session = Depends(get_session)):
    return [catalog.category_view(c) for c in db.scalars(select(Category).order_by(Category.name))]


@router.post("/admin/categories", dependencies=admin, status_code=201)
def create_category(data: CategoryWrite, db: Session = Depends(get_session)):
    return catalog.category_view(catalog.save(db, Category(**data.model_dump())))


@router.put("/admin/categories/{category_id}", dependencies=admin)
def update_category(category_id: UUID, data: CategoryWrite, db: Session = Depends(get_session)):
    c = catalog.get_record(db, Category, category_id)
    for key, value in data.model_dump().items():
        setattr(c, key, value)
    return catalog.category_view(catalog.save(db, c))


@router.get("/admin/products", dependencies=[Depends(require_admin)])
def admin_products(page: int = Query(1, ge=1, le=10000), db: Session = Depends(get_session)):
    return [
        catalog.product_view(p, admin=True)
        for p in db.scalars(select(Product).order_by(Product.id).offset((page - 1) * 24).limit(24))
    ]


@router.post("/admin/products", dependencies=admin, status_code=201)
def create_product(data: ProductWrite, db: Session = Depends(get_session)):
    catalog.get_record(db, Category, data.category_id)
    return catalog.product_view(catalog.save(db, Product(**data.model_dump())), admin=True)


@router.put("/admin/products/{product_id}", dependencies=admin)
def update_product(product_id: UUID, data: ProductWrite, db: Session = Depends(get_session)):
    p = catalog.get_record(db, Product, product_id)
    catalog.get_record(db, Category, data.category_id)
    for key, value in data.model_dump().items():
        setattr(p, key, value)
    catalog.save(db, p)
    db.expire(p, ["category"])
    return catalog.product_view(p, admin=True)


@router.post("/admin/products/{product_id}/variants", dependencies=admin, status_code=201)
def create_variant(product_id: UUID, data: VariantWrite, db: Session = Depends(get_session)):
    catalog.get_record(db, Product, product_id)
    v = ProductVariant(product_id=product_id, **data.model_dump())
    v.inventory = Inventory(on_hand=0, reserved=0)
    return catalog.variant_view(catalog.save(db, v))


@router.put("/admin/variants/{variant_id}", dependencies=admin)
def update_variant(variant_id: UUID, data: VariantWrite, db: Session = Depends(get_session)):
    v = catalog.get_record(db, ProductVariant, variant_id)
    for key, value in data.model_dump().items():
        setattr(v, key, value)
    return catalog.variant_view(catalog.save(db, v))


@router.put("/admin/variants/{variant_id}/stock", dependencies=admin)
def stock(variant_id: UUID, data: StockWrite, db: Session = Depends(get_session)):
    inventory = db.scalar(
        select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
    )
    if inventory is None:
        raise AppError(404, "not_found", "Inventory not found.")
    if data.on_hand < inventory.reserved:
        raise AppError(409, "reserved_stock", "Stock cannot fall below reserved quantities.")
    inventory.on_hand = data.on_hand
    catalog.save(db, inventory)
    return catalog.variant_view(inventory.variant)


@router.post("/admin/products/{product_id}/images", dependencies=admin, status_code=201)
def image(product_id: UUID, data: ImageWrite, db: Session = Depends(get_session)):
    catalog.get_record(db, Product, product_id)
    record = catalog.save(db, ProductImage(product_id=product_id, **data.model_dump(mode="json")))
    return {"id": str(record.id)}


@router.put("/admin/images/{image_id}", dependencies=admin)
def update_image(image_id: UUID, data: ImageWrite, db: Session = Depends(get_session)):
    record = catalog.get_record(db, ProductImage, image_id)
    for key, value in data.model_dump(mode="json").items():
        setattr(record, key, value)
    return {"id": str(catalog.save(db, record).id)}


@router.delete("/admin/images/{image_id}", dependencies=admin, status_code=204)
def delete_image(image_id: UUID, db: Session = Depends(get_session)):
    db.delete(catalog.get_record(db, ProductImage, image_id))
    db.commit()
    return Response(status_code=204)

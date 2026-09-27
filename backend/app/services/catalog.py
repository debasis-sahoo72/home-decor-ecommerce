from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.entities import (
    Category,
    Inventory,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    Review,
)


def save(db, record):
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            409, "catalog_conflict", "Slug, SKU, image or stock conflicts with existing data."
        ) from None
    return record


def get_record(db, model, record_id):
    record = db.get(model, record_id)
    if record is None:
        raise AppError(404, "not_found", "This item could not be found.")
    return record


def category_view(c):
    return dict(
        id=str(c.id),
        name=c.name,
        slug=c.slug,
        description=c.description,
        active=c.active,
        seo_title=c.seo_title,
        seo_description=c.seo_description,
    )


def variant_view(v):
    available = v.inventory.on_hand - v.inventory.reserved if v.inventory else 0
    discount = 0
    if v.compare_at_price:
        discount = int(
            ((v.compare_at_price - v.price) * 100 / v.compare_at_price).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
    return dict(
        id=str(v.id),
        sku=v.sku,
        label=v.label,
        price=str(v.price),
        compare_at_price=str(v.compare_at_price) if v.compare_at_price is not None else None,
        discount_percent=discount,
        active=v.active,
        available_stock=available,
        in_stock=v.active and available > 0,
    )


def product_view(p, admin=False):
    variants = sorted((v for v in p.variants if admin or v.active), key=lambda v: (v.price, v.sku))
    return dict(
        id=str(p.id),
        name=p.name,
        slug=p.slug,
        description=p.description,
        category=category_view(p.category),
        specifications=p.specifications,
        seo_title=p.seo_title,
        seo_description=p.seo_description,
        active=p.active,
        featured=p.featured,
        created_at=p.created_at.isoformat(),
        variants=[variant_view(v) for v in variants],
        images=[
            dict(
                id=str(i.id),
                public_id=i.public_id,
                url=i.url,
                alt=i.alt,
                width=i.width,
                height=i.height,
                position=i.position,
            )
            for i in sorted(p.images, key=lambda i: i.position)
        ],
        price=str(variants[0].price) if variants else None,
        in_stock=any(
            v.active and v.inventory and v.inventory.on_hand > v.inventory.reserved
            for v in variants
        ),
    )


def public_products():
    return (
        select(Product)
        .join(Category)
        .where(
            Product.active.is_(True),
            Product.archived_at.is_(None),
            Category.active.is_(True),
            Category.archived_at.is_(None),
            Product.variants.any(ProductVariant.active.is_(True)),
        )
        .options(
            selectinload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.inventory),
        )
    )


def detail(db, value, by_slug=False):
    p = db.scalar(
        public_products().where(Product.slug == value if by_slug else Product.id == value)
    )
    if p is None:
        raise AppError(404, "not_found", "This product is not available.")
    result = product_view(p)
    add_ratings(db, [result])
    return result


def add_ratings(db, items):
    if not items:
        return
    ratings = {
        str(pid): (float(avg), count)
        for pid, avg, count in db.execute(
            select(Review.product_id, func.avg(Review.rating), func.count())
            .where(Review.status == "published", Review.product_id.in_([p["id"] for p in items]))
            .group_by(Review.product_id)
        )
    }
    for item in items:
        avg, count = ratings.get(item["id"], (None, 0))
        item.update(rating=round(avg, 1) if avg else None, review_count=count)


def listing(db, query):
    price = (
        select(func.min(ProductVariant.price))
        .where(ProductVariant.product_id == Product.id, ProductVariant.active.is_(True))
        .correlate(Product)
        .scalar_subquery()
    )
    statement = public_products()
    if query.category:
        statement = statement.where(Category.slug == query.category)
    if query.q:
        # Same expression as the GIN index; no search infrastructure is needed.
        vector = func.to_tsvector(
            literal_column("'english'"), Product.name + " " + Product.description
        )
        statement = statement.where(
            vector.op("@@")(func.plainto_tsquery(literal_column("'english'"), query.q))
        )
    # Price and stock must match the SAME purchasable variant.
    eligible = select(ProductVariant.id).where(
        ProductVariant.product_id == Product.id, ProductVariant.active.is_(True)
    )
    if query.min_price is not None:
        eligible = eligible.where(ProductVariant.price >= query.min_price)
    if query.max_price is not None:
        eligible = eligible.where(ProductVariant.price <= query.max_price)
    if query.in_stock:
        eligible = eligible.join(Inventory).where(Inventory.on_hand > Inventory.reserved)
    statement = statement.where(eligible.exists())
    if query.featured:
        statement = statement.where(Product.featured.is_(True))
    sales = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order)
        .join(ProductVariant, ProductVariant.id == OrderItem.variant_id)
        .where(
            ProductVariant.product_id == Product.id,
            Order.status.in_(
                ["paid", "processing", "packed", "shipped", "out_for_delivery", "delivered"]
            ),
        )
        .correlate(Product)
        .scalar_subquery()
    )
    if query.sort == "best_sellers":
        statement = statement.where(sales > 0)
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    sort = {
        "newest": Product.created_at.desc(),
        "price_asc": price.asc(),
        "price_desc": price.desc(),
        "name": Product.name.asc(),
        "best_sellers": sales.desc(),
    }[query.sort]
    products = db.scalars(
        statement.order_by(sort, Product.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    items = [product_view(p) for p in products]
    add_ratings(db, items)
    return dict(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size,
        pages=(total + query.page_size - 1) // query.page_size,
    )

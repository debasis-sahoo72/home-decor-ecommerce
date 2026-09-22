"""Account wishlists; product uniqueness enforced by PostgreSQL."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import AppError
from app.models.entities import Product, Wishlist, WishlistItem
from app.services.catalog import add_ratings, product_view, public_products


def owner_list(db, user_id, create=False, lock=False):
    if create:
        db.execute(
            insert(Wishlist)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=[Wishlist.user_id])
        )
    query = select(Wishlist).where(Wishlist.user_id == user_id)
    return db.scalar(query.with_for_update() if lock else query)


def listing(db, user_id):
    wishlist = owner_list(db, user_id)
    ids = (
        list(
            db.scalars(
                select(WishlistItem.product_id)
                .where(WishlistItem.wishlist_id == wishlist.id)
                .order_by(WishlistItem.created_at.desc(), WishlistItem.id)
            )
        )
        if wishlist
        else []
    )
    products = (
        {p.id: product_view(p) for p in db.scalars(public_products().where(Product.id.in_(ids)))}
        if ids
        else {}
    )
    items = [products[i] for i in ids if i in products]
    add_ratings(db, items)
    return {
        "items": items,
        "product_ids": [str(i) for i in ids],
        "unavailable_ids": [str(i) for i in ids if i not in products],
    }


def add_products(db, user_id, product_ids, skip_unavailable=False):
    wishlist = owner_list(db, user_id, create=True, lock=True)
    valid = set(
        db.scalars(
            public_products().where(Product.id.in_(product_ids)).with_only_columns(Product.id)
        )
    )
    if not skip_unavailable and valid != set(product_ids):
        raise AppError(404, "not_found", "This product is no longer available.")
    existing = set(
        db.scalars(select(WishlistItem.product_id).where(WishlistItem.wishlist_id == wishlist.id))
    )
    if len(existing | valid) > 200:
        raise AppError(422, "wishlist_limit", "Your wishlist can hold up to 200 products.")
    for product_id in valid - existing:
        db.add(WishlistItem(wishlist_id=wishlist.id, product_id=product_id))
    db.commit()
    return listing(db, user_id)


def remove(db, user_id, product_id):
    wishlist = owner_list(db, user_id, lock=True)
    if wishlist:
        db.execute(
            delete(WishlistItem).where(
                WishlistItem.wishlist_id == wishlist.id, WishlistItem.product_id == product_id
            )
        )
    db.commit()

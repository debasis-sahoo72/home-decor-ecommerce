from sqlalchemy import func, select, update

from app.core.errors import AppError
from app.models.entities import Address, User


def lock_owner(db, user_id):
    db.scalar(select(User).where(User.id == user_id).with_for_update())


def owned(db, user_id, address_id):
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == user_id))
    if address is None:
        raise AppError(404, "address_not_found", "Address not found.")
    return address


def view(address):
    return dict(
        id=address.id,
        full_name=address.recipient,
        phone=address.phone,
        line1=address.line1,
        line2=address.line2,
        landmark=address.landmark,
        city=address.city,
        state=address.state,
        country=address.country,
        pincode=address.pincode,
        is_default=address.is_default,
    )


def listing(db, user_id):
    return [
        view(a)
        for a in db.scalars(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at, Address.id)
        )
    ]


def make_default(db, user_id, address):
    db.execute(
        update(Address)
        .where(Address.user_id == user_id, Address.is_default.is_(True))
        .values(is_default=False)
    )
    db.flush()
    address.is_default = True


def save(db, user_id, data, address_id=None):
    lock_owner(db, user_id)
    address = owned(db, user_id, address_id) if address_id else None
    count = db.scalar(select(func.count()).select_from(Address).where(Address.user_id == user_id))
    if address is None and count >= 20:
        raise AppError(
            422,
            "address_limit",
            "You can save up to 20 addresses. Edit or remove an existing address.",
        )
    values = data.model_dump(exclude={"full_name", "is_default"})
    values["recipient"] = data.full_name
    if address is None:
        address = Address(user_id=user_id, **values)
        db.add(address)
        db.flush()
    else:
        for name, value in values.items():
            setattr(address, name, value)
    # The first address is default; editing cannot accidentally leave no default.
    if data.is_default or count == 0:
        make_default(db, user_id, address)
    db.commit()
    return view(address)


def set_default(db, user_id, address_id):
    lock_owner(db, user_id)
    address = owned(db, user_id, address_id)
    make_default(db, user_id, address)
    db.commit()
    return view(address)


def remove(db, user_id, address_id):
    lock_owner(db, user_id)
    address = owned(db, user_id, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        replacement = db.scalar(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.created_at, Address.id)
            .limit(1)
        )
        if replacement:
            replacement.is_default = True
    db.commit()

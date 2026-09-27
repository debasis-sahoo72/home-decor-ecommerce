"""Explicit local administration; never expose this through public registration."""

import argparse
from datetime import UTC, datetime
from getpass import getpass

from sqlalchemy import delete, select

from app.core.security import hasher
from app.db import SessionLocal
from app.models.entities import AuthRateBucket, AuthSession, User
from app.schemas.auth import Registration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["create-admin", "cleanup-auth", "reconcile-checkout", "cleanup-media"]
    )
    args = parser.parse_args()
    if args.command == "cleanup-media":
        from app.config import get_settings
        from app.services.media import Cloudinary, cleanup

        with SessionLocal() as db:
            print(cleanup(db, Cloudinary(get_settings())))
        return
    if args.command == "reconcile-checkout":
        from app.config import get_settings
        from app.models.entities import Order
        from app.services import checkout
        from app.services.payment_provider import Razorpay

        provider = Razorpay(get_settings())
        with SessionLocal() as db:
            owners = list(
                db.scalars(
                    select(Order.user_id)
                    .where(
                        Order.status == "awaiting_payment",
                        Order.checkout_key.is_not(None),
                        Order.user_id.is_not(None),
                    )
                    .distinct()
                )
            )
        for user_id in owners:
            with SessionLocal() as db:
                try:
                    order = checkout.pending(db, user_id)
                    db.commit()
                    if order:
                        payment = checkout.payment_for(db, order)
                        if payment.provider_order_id:
                            result = checkout.confirm(db, user_id, order.id, provider)
                            print(f"{order.number}: {result['status']}")
                        elif payment.initiation_started:
                            print(
                                f"{order.number}: provider creation outcome requires manual reconciliation"
                            )
                except Exception:
                    db.rollback()
                    print(
                        "A pending checkout could not be reconciled; retry and inspect provider status."
                    )
        print("Checkout reconciliation complete. Started payments retain stock until reconciled.")
        return
    if args.command == "cleanup-auth":
        with SessionLocal.begin() as db:
            db.execute(delete(AuthSession).where(AuthSession.expires_at <= datetime.now(UTC)))
            db.execute(delete(AuthRateBucket).where(AuthRateBucket.expires_at <= datetime.now(UTC)))
        print("Expired authentication records removed.")
        return
    email, name = input("Admin email: "), input("Admin name: ")
    password = getpass("Passphrase (15–128 characters): ")
    if password != getpass("Repeat passphrase: "):
        raise SystemExit("Passphrases do not match.")
    try:
        data = Registration(email=email, name=name, password=password)
    except ValueError:
        raise SystemExit("Invalid email, name or passphrase. No account created.") from None
    with SessionLocal.begin() as db:
        if db.scalar(select(User).where(User.email == str(data.email))):
            raise SystemExit("Email already registered. No existing account was changed.")
        db.add(
            User(
                email=str(data.email),
                name=data.name,
                role="admin",
                status="active",
                password_hash=hasher.hash(password),
            )
        )
    print("Administrator created. Configure MFA before production launch.")


if __name__ == "__main__":
    main()

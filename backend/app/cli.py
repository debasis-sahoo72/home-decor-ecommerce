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
    parser.add_argument("command", choices=["create-admin", "cleanup-auth"])
    args = parser.parse_args()
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

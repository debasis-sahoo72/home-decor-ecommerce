"""Inspect delivery records or retry one definite failure/pending send by ID."""

import argparse
from uuid import UUID

from sqlalchemy import select

from app.db import SessionLocal
from app.models.entities import Notification
from app.services.notifications import deliver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry", type=UUID)
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.retry:
            deliver(db, args.retry)
        for row in db.scalars(
            select(Notification).order_by(Notification.created_at.desc()).limit(50)
        ):
            print(row.id, row.event, row.channel, row.status, row.attempts, row.error_code or "-")


if __name__ == "__main__":
    main()

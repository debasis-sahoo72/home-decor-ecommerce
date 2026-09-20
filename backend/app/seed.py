"""Idempotent reference data only: python -m app.seed."""

from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models.entities import Category


def main():
    with SessionLocal.begin() as db:
        for name, slug in [
            ("Lighting", "lighting"),
            ("Textiles", "textiles"),
            ("Decor objects", "decor-objects"),
        ]:
            db.execute(
                insert(Category)
                .values(name=name, slug=slug)
                .on_conflict_do_nothing(index_elements=[Category.slug])
            )
    print("Reference categories are ready; no users or delivery promises were seeded.")


if __name__ == "__main__":
    main()

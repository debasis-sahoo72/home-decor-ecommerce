from uuid import uuid4

from alembic.config import Config
from sqlalchemy import text

from alembic import command


def test_express_rows_migrate_to_standard_and_require_urban_review(pg_engine):
    with pg_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.downgrade(config, "0004")
            connection.execute(
                text(
                    "INSERT INTO delivery_pincodes (id,pincode,service,min_days,max_days,cutoff_hour,fee,active) VALUES (:id,'560001','next_day',1,1,12,50,true)"
                ),
                {"id": uuid4()},
            )
            command.upgrade(config, "head")
            row = (
                connection.execute(text("SELECT * FROM delivery_pincodes WHERE pincode='560001'"))
                .mappings()
                .one()
            )
            assert row["service"] == "standard"
            assert (row["min_days"], row["max_days"]) == (3, 5)
            assert row["urban"] is False
        finally:
            transaction.rollback()

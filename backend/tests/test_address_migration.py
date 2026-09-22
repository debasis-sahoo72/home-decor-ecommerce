from uuid import uuid4

from alembic.config import Config
from sqlalchemy import insert, text

from alembic import command
from app.models.entities import User


def test_existing_addresses_get_one_default_without_losing_data(pg_engine):
    with pg_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.downgrade(config, "0003")
            user = uuid4()
            connection.execute(
                insert(User).values(
                    id=user,
                    email="address-migration@example.com",
                    name="Migration test",
                    password_hash="not-a-login",
                )
            )
            for _ in range(2):
                connection.execute(
                    text(
                        "INSERT INTO addresses (id,user_id,recipient,phone,line1,city,state,pincode) VALUES (:id,:user,'Test Name','9876543210','12 Test Road','Bengaluru','Karnataka','560001')"
                    ),
                    {"id": uuid4(), "user": user},
                )
            command.upgrade(config, "head")
            rows = connection.execute(
                text("SELECT recipient,country,is_default FROM addresses WHERE user_id=:user"),
                {"user": user},
            ).all()
            assert len(rows) == 2
            assert all(row.recipient == "Test Name" and row.country == "IN" for row in rows)
            assert sum(row.is_default for row in rows) == 1
        finally:
            transaction.rollback()

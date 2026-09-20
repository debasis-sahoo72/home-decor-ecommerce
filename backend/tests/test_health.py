from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app

client = TestClient(app)


def test_liveness_does_not_require_database():
    with patch.object(
        app.state.engine, "connect", side_effect=AssertionError("DB must not be used")
    ):
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_success():
    connection = MagicMock()
    with patch.object(app.state.engine, "connect") as connect:
        connect.return_value.__enter__.return_value = connection
        response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"


def test_readiness_failure_hides_database_details():
    error = OperationalError("SELECT 1", {}, Exception("secret database details"))
    with patch.object(app.state.engine, "connect", side_effect=error):
        response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "database_unavailable",
        "message": "Database unavailable",
    }

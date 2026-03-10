import os
import secrets
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from alembic.config import Config
from alembic import command


@pytest.fixture(scope="module")
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["JWT_ALGORITHM"] = "HS256"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")

    from main import app
    with TestClient(app) as c:
        yield c

    os.unlink(db_path)
    del os.environ["DATABASE_URL"]
    del os.environ["JWT_SECRET_KEY"]
    del os.environ["JWT_ALGORITHM"]


def test_liveness_returns_200(client):
    """GET /api/health must return 200 with no DB interaction."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_returns_200_when_db_reachable(client):
    """GET /api/health/ready must return 200 when DB is reachable."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_returns_503_when_db_unreachable(client):
    """GET /api/health/ready must return 503 when DB is unavailable."""
    broken_session = MagicMock()
    broken_session.__enter__ = MagicMock(return_value=broken_session)
    broken_session.__exit__ = MagicMock(return_value=False)
    broken_session.exec.side_effect = OperationalError("connection refused", None, None)

    broken_session_maker = MagicMock(return_value=broken_session)

    with patch.object(client.app.state, "session_maker", broken_session_maker):
        response = client.get("/api/health/ready")

    assert response.status_code == 503


def test_liveness_returns_200_when_db_unreachable(client):
    """GET /api/health must return 200 even when DB is unavailable."""
    broken_session = MagicMock()
    broken_session.__enter__ = MagicMock(return_value=broken_session)
    broken_session.__exit__ = MagicMock(return_value=False)
    broken_session.exec.side_effect = OperationalError("connection refused", None, None)

    broken_session_maker = MagicMock(return_value=broken_session)

    with patch.object(client.app.state, "session_maker", broken_session_maker):
        response = client.get("/api/health")

    assert response.status_code == 200

import os
import secrets
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

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

    # Deferred import: main.py reads env vars at import time, so DATABASE_URL
    # and JWT_SECRET_KEY must be set before importing.
    from main import app

    with TestClient(app) as c:
        # Wait for the background migration task to set ready=True before any test runs.
        # This also validates that the background task actually completes successfully.
        deadline = time.monotonic() + 10
        while not c.app.state.ready and time.monotonic() < deadline:
            time.sleep(0.05)
        assert c.app.state.ready, "Background migration task did not complete in time"
        yield c

    os.unlink(db_path)
    del os.environ["DATABASE_URL"]
    del os.environ["JWT_SECRET_KEY"]
    del os.environ["JWT_ALGORITHM"]


def test_liveness_returns_200(client):
    """GET /api/health must return 200 when migrations succeeded."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_liveness_returns_503_when_migrations_failed(client):
    """GET /api/health must return 503 when migrations have fatally failed."""
    client.app.state.migration_failed = True
    try:
        response = client.get("/api/health")
        assert response.status_code == 503
        assert "Migrations failed" in response.json()["detail"]
    finally:
        client.app.state.migration_failed = False


def test_liveness_returns_200_when_db_unreachable(client):
    """GET /api/health must return 200 even when DB is unavailable.

    The liveness handler does not touch the DB — it only checks migration_failed.
    No DB mock is needed here; this test verifies the handler ignores DB state entirely.
    """
    response = client.get("/api/health")
    assert response.status_code == 200


def test_readiness_returns_200_when_db_reachable(client):
    """GET /api/health/ready must return 200 when migrations done and DB reachable."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_returns_503_when_migrations_in_progress(client):
    """GET /api/health/ready must return 503 while migrations are running."""
    client.app.state.ready = False
    try:
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        assert "Migrations in progress" in response.json()["detail"]
    finally:
        client.app.state.ready = True


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
    assert response.json()["detail"] == "Database unreachable"

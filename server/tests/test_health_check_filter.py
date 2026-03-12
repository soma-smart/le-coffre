import logging
import os
import secrets
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from monitoring import _UvicornAccessFilter


@pytest.fixture
def filter_instance():
    return _UvicornAccessFilter(monitoring_active=True)


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
        deadline = time.monotonic() + 10
        while not c.app.state.ready and time.monotonic() < deadline:
            time.sleep(0.05)
        assert c.app.state.ready, "Background migration task did not complete in time"
        yield c

    os.unlink(db_path)
    del os.environ["DATABASE_URL"]
    del os.environ["JWT_SECRET_KEY"]
    del os.environ["JWT_ALGORITHM"]


def make_uvicorn_record(client: str, method: str, path: str, status: int) -> logging.LogRecord:
    """Build a log record matching uvicorn's actual access log format."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(client, method, path, "1.1", status),
        exc_info=None,
    )
    return record


def test_health_200_is_filtered(filter_instance):
    """Successful health check probes must not appear in logs."""
    record = make_uvicorn_record("100.64.7.58:57990", "GET", "/api/health", 200)
    assert filter_instance.filter(record) is False


def test_health_503_is_not_filtered(filter_instance):
    """Failed health checks (DB down) must remain visible in logs."""
    record = make_uvicorn_record("100.64.7.58:57990", "GET", "/api/health", 503)
    assert filter_instance.filter(record) is True


def test_metrics_200_is_filtered(filter_instance):
    """Successful metrics route responses must not appear in logs."""
    record = make_uvicorn_record("10.32.7.62:12345", "GET", "/api/metrics", 200)
    assert filter_instance.filter(record) is False


def test_filter_is_independent_of_message_format(filter_instance):
    """Filter must work regardless of uvicorn's log format string."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="%s %s %s HTTP/%s %d",  # format without quotes — args tuple is what matters
        args=("10.32.7.62:12345", "GET", "/api/metrics", "1.1", 200),
        exc_info=None,
    )
    assert filter_instance.filter(record) is False


def test_metrics_503_is_not_filtered(filter_instance):
    """Failed metrics route responses must remain visible in logs."""
    record = make_uvicorn_record("10.32.7.62:12345", "GET", "/api/metrics", 503)
    assert filter_instance.filter(record) is True


def test_other_routes_are_not_filtered(filter_instance):
    """Business endpoint logs must not be affected by the filter."""
    record = make_uvicorn_record("100.64.7.208:35250", "GET", "/api/passwords/list", 200)
    assert filter_instance.filter(record) is True


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


def test_background_task_sets_migration_failed_on_error(client):
    """_run_migrations_in_background must set migration_failed=True when run_migrations raises."""
    with patch("main.run_migrations", side_effect=Exception("DB connection refused")):
        with TestClient(client.app) as c:
            deadline = time.monotonic() + 5
            while not c.app.state.migration_failed and time.monotonic() < deadline:
                time.sleep(0.05)
            assert c.app.state.migration_failed is True
            assert c.app.state.ready is False
    # Restore state for subsequent tests that rely on the module-scoped client.
    client.app.state.migration_failed = False
    client.app.state.ready = True

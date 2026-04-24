import os
import secrets
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).parent


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-apply the `unit` / `integration` / `e2e` markers based on each test's
    path so `pytest -m <profile>` partitions the suite without per-file annotations.

    Rules (first match wins):
      `<context>/unit/`        → unit
      `e2e/`                   → e2e
      anything else under tests/ → integration

    The "anything else" catch-all covers `<context>/integration/`, `tests/alembic/`,
    `tests/security/`, `tests/shared_kernel/**` (excluding /unit/), and the
    top-level middleware tests (`tests/test_*.py`) — all of which spin up real
    adapters, in-memory SQLite, or a TestClient.
    """
    for item in items:
        rel = Path(item.fspath).relative_to(_TESTS_ROOT).as_posix()
        if "/unit/" in f"/{rel}":
            item.add_marker(pytest.mark.unit)
        elif rel.startswith("e2e/"):
            item.add_marker(pytest.mark.e2e)
        else:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def env_vars():
    os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["JWT_ALGORITHM"] = "HS256"
    # Use very high rate limits so e2e tests aren't impacted by incidental traffic;
    # the dedicated rate-limit workflow overrides these on app.state for its scenarios.
    os.environ["RATE_LIMIT_USER_MAX_REQUESTS"] = "10000"
    os.environ["RATE_LIMIT_UNAUTH_MAX_REQUESTS"] = "10000"
    os.environ["RATE_LIMIT_AUTH_MAX_REQUESTS"] = "10000"
    # Shorten the lockout window so PHASE 7 can exercise the lock→wait→retry
    # cycle end-to-end without making the suite sleep for minutes. The default
    # (5 failures / 300s) is preserved in production; tests only care that the
    # gateway honors *some* finite window and that the use case clears state
    # when it elapses.
    os.environ["LOGIN_LOCKOUT_SECONDS"] = "1"
    yield
    for key in (
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "RATE_LIMIT_USER_MAX_REQUESTS",
        "RATE_LIMIT_UNAUTH_MAX_REQUESTS",
        "RATE_LIMIT_AUTH_MAX_REQUESTS",
        "LOGIN_LOCKOUT_SECONDS",
    ):
        os.environ.pop(key, None)

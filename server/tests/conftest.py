import os
import secrets

import pytest


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

import os
import secrets

import pytest


@pytest.fixture(scope="session")
def env_vars():
    os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["JWT_ALGORITHM"] = "HS256"
    # Use very high rate limits so e2e tests are not impacted by the defaults.
    os.environ["RATE_LIMIT_USER_MAX_REQUESTS"] = "10000"
    os.environ["RATE_LIMIT_UNAUTH_MAX_REQUESTS"] = "10000"
    os.environ["RATE_LIMIT_AUTH_MAX_REQUESTS"] = "10000"
    # Disable login lockout in e2e by default (raise threshold and set a tiny
    # window so any residual lockout from a previous test decays immediately).
    os.environ["LOGIN_MAX_FAILED_ATTEMPTS"] = "10000"
    os.environ["LOGIN_LOCKOUT_SECONDS"] = "1"
    yield
    for key in (
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "RATE_LIMIT_USER_MAX_REQUESTS",
        "RATE_LIMIT_UNAUTH_MAX_REQUESTS",
        "RATE_LIMIT_AUTH_MAX_REQUESTS",
        "LOGIN_MAX_FAILED_ATTEMPTS",
        "LOGIN_LOCKOUT_SECONDS",
    ):
        os.environ.pop(key, None)

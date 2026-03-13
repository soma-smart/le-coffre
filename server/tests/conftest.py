import os
import secrets

import pytest


@pytest.fixture(scope="session")
def env_vars():
    os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["JWT_ALGORITHM"] = "HS256"
    # Use very high rate limits so e2e tests are not impacted
    os.environ["RATE_LIMIT_AUTH_MAX_REQUESTS"] = "1000"
    os.environ["RATE_LIMIT_API_MAX_REQUESTS"] = "1000"
    yield
    del os.environ["JWT_SECRET_KEY"]
    del os.environ["JWT_ALGORITHM"]
    os.environ.pop("RATE_LIMIT_AUTH_MAX_REQUESTS", None)
    os.environ.pop("RATE_LIMIT_API_MAX_REQUESTS", None)

import pytest
from conftest import CsrfTestClient

from main import app


@pytest.fixture
def rate_limited_client(database, env_vars):
    with CsrfTestClient(app) as client:
        # Override rate limits on the live app state (lifespan already ran)
        app.state.rate_limit_auth_max_requests = 3
        app.state.rate_limit_api_max_requests = 5
        app.state.rate_limit_window_seconds = 60
        # Clear any state left by previous tests so each test starts with a
        # clean slate — the rate limiter is a singleton on the shared app object.
        app.state.rate_limiter.reset()
        yield client


class TestRateLimitingWorkflow:
    def test_should_return_429_when_login_rate_limit_exceeded(
        self, rate_limited_client
    ):
        # Disable auto-CSRF: the CSRF endpoint requires auth and always returns 401
        # when unauthenticated, so the token is never cached and each POST would
        # waste 2 API bucket slots (one CSRF fetch + one POST).  We're testing
        # auth rate limiting here — CSRF is orthogonal.
        rate_limited_client.disable_auto_csrf()

        for _ in range(3):
            r = rate_limited_client.post(
                "/api/auth/login",
                json={"email": "test@x.com", "password": "wrong"},
            )
            assert r.status_code != 429

        r = rate_limited_client.post(
            "/api/auth/login",
            json={"email": "test@x.com", "password": "wrong"},
        )
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]
        assert "Retry-After" in r.headers

    def test_should_return_429_when_api_rate_limit_exceeded(self, rate_limited_client):
        for _ in range(5):
            r = rate_limited_client.get("/api/health")  # exempt, won't count
            assert r.status_code == 200

        # API route that isn't auth — limited at 5
        for i in range(5):
            r = rate_limited_client.get("/api/vault/status")
            assert r.status_code != 429, f"Blocked too early on request {i + 1}"

        r = rate_limited_client.get("/api/vault/status")
        assert r.status_code == 429

    def test_should_not_rate_limit_health_check(self, rate_limited_client):
        for _ in range(20):
            r = rate_limited_client.get("/api/health")
            assert r.status_code == 200

    def test_should_include_rate_limit_headers(self, rate_limited_client):
        r = rate_limited_client.get("/api/vault/status")
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers

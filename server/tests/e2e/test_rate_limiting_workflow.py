import pytest
from conftest import CsrfTestClient
from identity_access_management_context.adapters.secondary import (
    InMemoryLoginLockoutGateway,
)
from main import app


@pytest.fixture
def rate_limited_client(database, env_vars):
    with CsrfTestClient(app) as client:
        # Override limits on the live app state (lifespan already ran).
        app.state.rate_limit_user_max_requests = 10
        app.state.rate_limit_unauth_max_requests = 5
        app.state.rate_limit_auth_max_requests = 3
        app.state.rate_limit_window_seconds = 60
        # Reset singleton state between tests.
        app.state.rate_limiter.reset()
        app.state.login_lockout_gateway.reset()
        yield client


class TestRateLimitingWorkflow:
    def test_auth_floor_blocks_login_with_429_after_limit(self, rate_limited_client: CsrfTestClient):
        # Disable auto-CSRF — /auth/csrf-token is authenticated-only and every POST
        # would otherwise consume 2 bucket slots from the CSRF fetch alone.
        rate_limited_client.disable_auto_csrf()

        for _ in range(3):
            r = rate_limited_client.post(
                "/api/auth/login",
                json={"email": "never@example.com", "password": "wrong"},
            )
            assert r.status_code != 429

        r = rate_limited_client.post(
            "/api/auth/login",
            json={"email": "never@example.com", "password": "wrong"},
        )
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]
        assert int(r.headers["Retry-After"]) > 0

    def test_unauth_ip_bucket_blocks_generic_api_routes(self, rate_limited_client: CsrfTestClient):
        # /api/vault/status is unauthenticated-readable; exhausts unauth_max=5
        for i in range(5):
            r = rate_limited_client.get("/api/vault/status")
            assert r.status_code != 429, f"Blocked too early on request {i + 1}"

        r = rate_limited_client.get("/api/vault/status")
        assert r.status_code == 429

    def test_health_is_not_rate_limited(self, rate_limited_client: CsrfTestClient):
        for _ in range(50):
            assert rate_limited_client.get("/api/health").status_code == 200

    def test_rate_limit_headers_are_included(self, rate_limited_client: CsrfTestClient):
        r = rate_limited_client.get("/api/vault/status")
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers

    def test_read_only_sso_routes_do_not_consume_auth_floor(self, rate_limited_client: CsrfTestClient):
        rate_limited_client.disable_auto_csrf()
        # Hit read-only SSO routes many times; must NOT saturate the auth floor.
        # Each call still consumes unauth IP bucket slots, so we unauth-raise first.
        app.state.rate_limit_unauth_max_requests = 100

        for _ in range(20):
            # These endpoints exist unauthenticated and return 200/404, never 429
            assert rate_limited_client.get("/api/auth/sso/is-configured").status_code != 429

        # The auth floor (3) is still untouched — 3 login attempts must succeed (reach 401)
        for _ in range(3):
            r = rate_limited_client.post(
                "/api/auth/login",
                json={"email": "never@example.com", "password": "wrong"},
            )
            assert r.status_code == 401

        # 4th hits the auth floor
        r = rate_limited_client.post(
            "/api/auth/login",
            json={"email": "never@example.com", "password": "wrong"},
        )
        assert r.status_code == 429


class TestLoginLockoutWorkflow:
    def test_five_failed_logins_lock_the_account_with_retry_after(self, rate_limited_client: CsrfTestClient):
        rate_limited_client.disable_auto_csrf()

        # Raise BOTH the auth-floor and the unauthenticated principal limit so
        # neither rate-limit 429 masks the lockout 401 we're trying to observe.
        app.state.rate_limit_auth_max_requests = 100
        app.state.rate_limit_unauth_max_requests = 100

        # Reinstall a lockout with the spec values (the fixture may override them).
        app.state.login_lockout_gateway = InMemoryLoginLockoutGateway(max_failures=5, lockout_seconds=300)

        email = "locked-target@example.com"
        for i in range(5):
            r = rate_limited_client.post(
                "/api/auth/login",
                json={"email": email, "password": "wrong"},
            )
            assert r.status_code == 401, f"Attempt {i + 1} status={r.status_code}"

        # 6th attempt: lockout should fire — status is still 401 (not 429),
        # but the detail string and Retry-After distinguish it.
        r = rate_limited_client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong"},
        )
        assert r.status_code == 401
        assert "locked" in r.json()["detail"].lower()
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) > 0

    def test_lockout_is_per_email_not_per_ip(self, rate_limited_client: CsrfTestClient):
        """Failed attempts against account A do not lock account B from the same IP."""
        rate_limited_client.disable_auto_csrf()
        app.state.rate_limit_auth_max_requests = 100
        app.state.rate_limit_unauth_max_requests = 100

        app.state.login_lockout_gateway = InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=300)

        # Lock account A
        for _ in range(3):
            rate_limited_client.post(
                "/api/auth/login",
                json={"email": "a@example.com", "password": "wrong"},
            )
        r_a = rate_limited_client.post(
            "/api/auth/login",
            json={"email": "a@example.com", "password": "wrong"},
        )
        assert r_a.status_code == 401
        assert "locked" in r_a.json()["detail"].lower()

        # Account B is unaffected — still gets plain "Invalid credentials" 401
        r_b = rate_limited_client.post(
            "/api/auth/login",
            json={"email": "b@example.com", "password": "wrong"},
        )
        assert r_b.status_code == 401
        assert "locked" not in r_b.json()["detail"].lower()

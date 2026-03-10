from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from identity_access_management_context.application.gateways import Token
from security.rate_limit_middleware import RateLimitMiddleware
from security.rate_limiter import InMemoryRateLimiter


class _FakeTokenGateway:
    """Minimal token gateway for middleware unit tests."""

    def __init__(self) -> None:
        self._tokens: dict[str, Token] = {}

    def register(self, token: str, user_id: str) -> None:
        self._tokens[token] = Token(value=token, user_id=UUID(user_id), email="", roles=[], claims={})

    async def validate_token(self, token: str) -> Token | None:
        return self._tokens.get(token)


def _create_app(
    auth_max: int = 5,
    api_max: int = 60,
    window: int = 60,
    login_status_code: int = 401,
    token_gateway: _FakeTokenGateway | None = None,
) -> FastAPI:
    """
    Build a minimal FastAPI app with the rate-limit middleware.

    ``login_status_code`` controls what the ``/auth/login`` endpoint returns.
    Defaults to 401 (failed login) so tests can exhaust the auth bucket without
    the success-reset kicking in.  Pass 200 to test the reset path.

    ``token_gateway`` is used for per-user rate limiting on non-auth routes.
    Pass a ``_FakeTokenGateway`` instance with pre-registered tokens to enable
    user-based checks.  Defaults to ``None`` (user check skipped).
    """
    app = FastAPI(root_path="/api")

    rate_limiter = InMemoryRateLimiter()
    app.state.rate_limiter = rate_limiter
    app.state.rate_limit_auth_max_requests = auth_max
    app.state.rate_limit_api_max_requests = api_max
    app.state.rate_limit_window_seconds = window
    app.state.token_gateway = token_gateway

    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health():
        return PlainTextResponse("ok")

    @app.get("/passwords")
    async def passwords():
        return PlainTextResponse("passwords")

    @app.post("/auth/login")
    async def login():
        return PlainTextResponse("login", status_code=login_status_code)

    @app.get("/other")
    async def other():
        return PlainTextResponse("other")

    return app


@pytest.fixture
def app() -> FastAPI:
    # api_max=5, auth_max=3; login_status_code=401 so auth resets don't interfere
    return _create_app(auth_max=3, api_max=5, window=60, login_status_code=401)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class TestRateLimitMiddleware:
    def test_should_exempt_health_check(self, client: TestClient):
        for _ in range(10):
            r = client.get("/api/health")
            assert r.status_code == 200

    def test_should_exempt_docs(self, client: TestClient):
        for _ in range(10):
            r = client.get("/docs")
            assert r.status_code in (200, 404)  # may not exist, but not 429

    def test_should_block_api_routes_over_limit(self, client: TestClient):
        # api_max=5; 6th request must be blocked
        for _ in range(5):
            r = client.get("/api/passwords")
            assert r.status_code == 200

        r = client.get("/api/passwords")
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_should_include_rate_limit_headers_on_api_success(self, client: TestClient):
        r = client.get("/api/passwords")
        assert r.status_code == 200
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers

    def test_should_block_auth_routes_over_limit(self, client: TestClient):
        # login returns 401 (failed creds) → no reset → bucket exhausts normally
        for _ in range(3):
            r = client.post("/api/auth/login")
            assert r.status_code == 401

        r = client.post("/api/auth/login")
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_should_include_rate_limit_headers_on_auth_success(self, client: TestClient):
        # Auth routes expose the auth-bucket limit in headers (the stricter one)
        r = client.post("/api/auth/login")
        assert r.status_code == 401  # failed creds, not yet rate-limited
        assert "X-RateLimit-Limit" in r.headers
        assert int(r.headers["X-RateLimit-Limit"]) == 3  # auth_max, not api_max
        assert "X-RateLimit-Remaining" in r.headers

    def test_should_include_retry_after_header_on_auth_429(self, client: TestClient):
        for _ in range(3):
            client.post("/api/auth/login")

        r = client.post("/api/auth/login")
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) > 0

    def test_should_include_retry_after_header_on_api_429(self, client: TestClient):
        for _ in range(5):
            client.get("/api/passwords")

        r = client.get("/api/passwords")
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) > 0

    def test_auth_and_api_buckets_are_independent(self):
        """Auth bucket exhaustion only blocks auth routes; API routes use a separate bucket."""
        # Use a high api_max so the small number of auth requests never saturates it
        app = _create_app(auth_max=3, api_max=20, window=60, login_status_code=401)

        with TestClient(app) as c:
            # Exhaust the auth bucket (3 pass + 1 blocked = 4 total, all counted by API bucket)
            for _ in range(3):
                c.post("/api/auth/login")
            assert c.post("/api/auth/login").status_code == 429

            # API bucket has 4 of 20 slots used — password endpoint is unaffected
            for _ in range(10):
                assert c.get("/api/passwords").status_code == 200

    def test_should_not_rate_limit_non_api_routes(self):
        app = FastAPI()
        app.state.rate_limiter = InMemoryRateLimiter()
        app.state.rate_limit_auth_max_requests = 1
        app.state.rate_limit_api_max_requests = 1
        app.state.rate_limit_window_seconds = 60
        app.state.token_gateway = None
        app.add_middleware(RateLimitMiddleware)

        @app.get("/something")
        async def something():
            return PlainTextResponse("ok")

        with TestClient(app) as c:
            for _ in range(5):
                r = c.get("/something")
                assert r.status_code == 200

    def test_should_handle_concurrent_requests_safely(self, client: TestClient):
        """Verify rate limiter is thread-safe under concurrent load on auth routes."""

        def make_request():
            return client.post("/api/auth/login")

        # Launch 10 concurrent requests against auth limit of 3
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        allowed = [r for r in results if r.status_code != 429]
        limited = [r for r in results if r.status_code == 429]

        # Exactly auth_max=3 should pass, the rest must be rate-limited
        assert len(allowed) == 3, f"Expected 3 allowed, got {len(allowed)}"
        assert len(limited) == 7, f"Expected 7 rate-limited, got {len(limited)}"

    def test_should_rate_limit_authenticated_user_on_api_routes(self):
        """
        When a valid access_token cookie is present, the per-user bucket is
        checked independently of the IP bucket.  Exceeding api_max requests
        from the same user blocks that user even if the IP bucket still has
        capacity.
        """
        user_id = "00000000-0000-0000-0000-000000000001"
        token = "user-token"
        gateway = _FakeTokenGateway()
        gateway.register(token, user_id)

        # api_max=3; a high IP max ensures IP bucket never blocks before user bucket
        app = _create_app(auth_max=100, api_max=3, window=60, token_gateway=gateway)

        with TestClient(app) as c:
            c.cookies.set("access_token", token)

            for i in range(3):
                r = c.get("/api/passwords")
                assert r.status_code == 200, f"Request {i + 1} should not be limited"

            # 4th request: user bucket exhausted
            r = c.get("/api/passwords")
            assert r.status_code == 429
            assert "Too many requests" in r.json()["detail"]

    def test_user_buckets_are_independent_of_each_other(self):
        """
        Two authenticated users on different IPs have independent user buckets;
        one user being rate-limited must not affect the other.
        """
        user_a = "00000000-0000-0000-0000-000000000001"
        user_b = "00000000-0000-0000-0000-000000000002"
        token_a, token_b = "token-a", "token-b"
        gateway = _FakeTokenGateway()
        gateway.register(token_a, user_a)
        gateway.register(token_b, user_b)

        # api_max=2; users come from separate IPs so the shared IP bucket
        # of one cannot bleed into the other
        app = _create_app(auth_max=100, api_max=2, window=60, token_gateway=gateway)

        with TestClient(app) as c_a, TestClient(app) as c_b:
            c_a.cookies.set("access_token", token_a)
            c_b.cookies.set("access_token", token_b)
            ip_a = {"X-Forwarded-For": "10.0.0.1"}
            ip_b = {"X-Forwarded-For": "10.0.0.2"}

            # Exhaust user A's bucket from IP-A
            for _ in range(2):
                c_a.get("/api/passwords", headers=ip_a)
            assert c_a.get("/api/passwords", headers=ip_a).status_code == 429

            # User B (from IP-B) is unaffected — their user bucket is still empty
            for _ in range(2):
                r = c_b.get("/api/passwords", headers=ip_b)
                assert r.status_code == 200

    def test_unauthenticated_requests_skip_user_check(self):
        """
        Requests without an access_token cookie are not checked against a user
        bucket — only the IP bucket applies.
        """
        app = _create_app(auth_max=100, api_max=3, window=60, token_gateway=_FakeTokenGateway())

        with TestClient(app) as c:
            for _ in range(3):
                r = c.get("/api/passwords")  # no cookie
                assert r.status_code == 200

            # IP bucket exhausted
            r = c.get("/api/passwords")
            assert r.status_code == 429

    def test_user_check_does_not_apply_to_auth_routes(self):
        """
        Auth routes are NOT subject to the per-user check.  Even if the user
        bucket is exhausted, the user can still reach the login endpoint and
        will only be blocked once the auth bucket is exhausted.

        Two different IPs are used so that exhausting the user bucket (from
        IP-A) does not also exhaust the IP bucket seen by the auth request
        (from IP-B).
        """
        user_id = "00000000-0000-0000-0000-000000000001"
        token = "user-token"
        gateway = _FakeTokenGateway()
        gateway.register(token, user_id)

        # api_max=3 (tight user bucket); auth_max=5 (won't interfere)
        app = _create_app(
            auth_max=5,
            api_max=3,
            window=60,
            login_status_code=401,
            token_gateway=gateway,
        )

        ip_a = {"X-Forwarded-For": "10.0.0.1"}
        ip_b = {"X-Forwarded-For": "10.0.0.2"}

        with TestClient(app) as c:
            c.cookies.set("access_token", token)

            # Exhaust the user bucket from IP-A
            for _ in range(3):
                c.get("/api/passwords", headers=ip_a)
            # Confirm user bucket is gone
            assert c.get("/api/passwords", headers=ip_a).status_code == 429

            # From a fresh IP (IP-B), the auth route must still work — the user
            # bucket exhaustion must not bleed into auth route checks.
            r = c.post("/api/auth/login", headers=ip_b)
            assert r.status_code == 401, (
                "Auth route should not be blocked by user bucket; expected 401 (wrong creds), got 429"
            )

    def test_should_reset_auth_limit_but_not_api_limit_on_successful_login(self):
        """
        A successful login resets the **auth** bucket only.  The API bucket
        keeps accumulating so that a client cannot bypass the general API limit
        by logging in repeatedly.
        """
        # auth_max=2, api_max=3; login returns 200 (success)
        app = _create_app(auth_max=2, api_max=3, window=60, login_status_code=200)

        with TestClient(app) as c:
            # Three successful logins; auth bucket fills then resets after each.
            # The API bucket counts every login but is never reset.
            for i in range(3):
                r = c.post("/api/auth/login")
                assert r.status_code == 200, f"Login {i + 1} should not be rate-limited"

            # api_max=3 was incremented by all 3 logins without ever being reset.
            # The API bucket is now exhausted — next request to any /api route is blocked.
            r = c.get("/api/passwords")
            assert r.status_code == 429, "API bucket should be exhausted after 3 logins counted against it"

    def test_should_reset_rate_limit_after_successful_login(self):
        """
        A successful login (2xx) resets the auth IP bucket so that legitimate
        users on shared IPs (e.g. office NAT) are never permanently locked out
        of the login page.
        """
        # auth_max=2; login returns 200 (success); api_max is high so it never blocks
        app = _create_app(auth_max=2, api_max=100, window=60, login_status_code=200)

        with TestClient(app) as c:
            # Without the reset, the 3rd request would exceed auth_max=2 and return 429.
            # With the reset, each successful login clears the bucket — all succeed.
            for i in range(6):
                r = c.post("/api/auth/login")
                assert r.status_code == 200, f"Request {i + 1} should not be rate-limited"

    def test_should_not_reset_rate_limit_on_failed_login(self):
        """
        A failed login (non-2xx) does NOT reset the bucket; successive failures
        accumulate until the IP is blocked.
        """
        app = _create_app(auth_max=3, api_max=100, window=60, login_status_code=401)

        with TestClient(app) as c:
            for _ in range(3):
                r = c.post("/api/auth/login")
                assert r.status_code == 401  # failed credentials, bucket fills

            r = c.post("/api/auth/login")
            assert r.status_code == 429  # bucket exhausted, IP blocked

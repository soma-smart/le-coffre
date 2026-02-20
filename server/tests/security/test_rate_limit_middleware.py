import pytest

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from security.rate_limiter import InMemoryRateLimiter
from security.rate_limit_middleware import RateLimitMiddleware


def _create_app(
    auth_max: int = 5,
    api_max: int = 60,
    window: int = 60,
) -> FastAPI:
    """Build a minimal FastAPI app with the rate-limit middleware."""
    app = FastAPI(root_path="/api")

    rate_limiter = InMemoryRateLimiter()
    app.state.rate_limiter = rate_limiter
    app.state.rate_limit_auth_max_requests = auth_max
    app.state.rate_limit_api_max_requests = api_max
    app.state.rate_limit_window_seconds = window
    app.state.token_gateway = None  # No auth for middleware unit tests

    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health():
        return PlainTextResponse("ok")

    @app.get("/passwords")
    async def passwords():
        return PlainTextResponse("passwords")

    @app.post("/auth/login")
    async def login():
        return PlainTextResponse("login")

    @app.get("/other")
    async def other():
        return PlainTextResponse("other")

    return app


@pytest.fixture
def app() -> FastAPI:
    return _create_app(auth_max=3, api_max=5, window=60)


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

    def test_should_allow_api_requests_under_limit(self, client: TestClient):
        for _ in range(5):
            r = client.get("/api/passwords")
            assert r.status_code == 200

    def test_should_block_api_requests_over_limit(self, client: TestClient):
        for _ in range(5):
            client.get("/api/passwords")

        r = client.get("/api/passwords")
        assert r.status_code == 429
        body = r.json()
        assert "Too many requests" in body["detail"]

    def test_should_apply_stricter_limit_on_auth_routes(self, client: TestClient):
        for _ in range(3):
            r = client.post("/api/auth/login")
            assert r.status_code == 200

        r = client.post("/api/auth/login")
        assert r.status_code == 429

    def test_should_include_rate_limit_headers_on_success(self, client: TestClient):
        r = client.get("/api/passwords")
        assert r.status_code == 200
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers

    def test_should_include_retry_after_header_on_429(self, client: TestClient):
        for _ in range(5):
            client.get("/api/passwords")

        r = client.get("/api/passwords")
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) > 0

    def test_should_track_auth_and_api_routes_separately(self, client: TestClient):
        # Exhaust auth limit (3)
        for _ in range(3):
            client.post("/api/auth/login")

        r = client.post("/api/auth/login")
        assert r.status_code == 429

        # API routes should still work (separate counter)
        r = client.get("/api/passwords")
        assert r.status_code == 200

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
        """Verify rate limiter is thread-safe under concurrent load."""

        def make_request():
            return client.get("/api/passwords")

        # Launch 10 concurrent requests (limit is 5)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # Count responses
        success = [r for r in results if r.status_code == 200]
        limited = [r for r in results if r.status_code == 429]

        # Exactly 5 should succeed, 5 should be rate-limited
        assert len(success) == 5, f"Expected 5 successful, got {len(success)}"
        assert len(limited) == 5, f"Expected 5 rate-limited, got {len(limited)}"

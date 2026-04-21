from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from shared_kernel.adapters.primary.rate_limit_middleware import RateLimitMiddleware
from shared_kernel.adapters.secondary.in_memory_rate_limiter import InMemoryRateLimiter
from shared_kernel.application.gateways import Principal
from starlette.testclient import TestClient


class _FakePrincipalResolver:
    """Minimal PrincipalResolver for middleware unit tests."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}  # token -> user_id

    def register(self, token: str, user_id: str) -> None:
        self._tokens[token] = user_id

    async def resolve(self, access_token: str | None, fallback_ip: str) -> Principal:
        if not access_token:
            return Principal(kind="ip", id=fallback_ip)
        user_id = self._tokens.get(access_token)
        if user_id is None:
            return Principal(kind="ip", id=fallback_ip)
        return Principal(kind="user", id=user_id)


def _create_app(
    *,
    user_max: int = 300,
    unauth_max: int = 30,
    auth_max: int = 100,
    window: int = 60,
    login_status_code: int = 401,
    principal_resolver: _FakePrincipalResolver | None = None,
    trusted_proxies: set[str] | None = None,
    trusted_proxy_hops: int = 1,
) -> FastAPI:
    app = FastAPI(root_path="/api")

    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.rate_limit_user_max_requests = user_max
    app.state.rate_limit_unauth_max_requests = unauth_max
    app.state.rate_limit_auth_max_requests = auth_max
    app.state.rate_limit_window_seconds = window
    app.state.rate_limit_trusted_proxies = trusted_proxies if trusted_proxies is not None else {"127.0.0.1", "::1"}
    app.state.rate_limit_trusted_proxy_hops = trusted_proxy_hops
    app.state.principal_resolver = principal_resolver if principal_resolver is not None else _FakePrincipalResolver()

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

    @app.post("/auth/register-admin")
    async def register_admin():
        return PlainTextResponse("registered", status_code=200)

    @app.post("/auth/refresh-token")
    async def refresh_token():
        return PlainTextResponse("refreshed", status_code=200)

    @app.get("/auth/sso/callback")
    async def sso_callback():
        return PlainTextResponse("sso-ok", status_code=200)

    @app.get("/auth/sso/url")
    async def sso_url():
        return PlainTextResponse("url", status_code=200)

    @app.get("/auth/sso/is-configured")
    async def sso_is_configured():
        return PlainTextResponse("configured", status_code=200)

    @app.get("/other")
    async def other():
        return PlainTextResponse("other")

    return app


@pytest.fixture
def app() -> FastAPI:
    return _create_app(user_max=10, unauth_max=5, auth_max=3, window=60)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class TestExemptPaths:
    def test_health_is_exempt(self, client: TestClient):
        for _ in range(20):
            assert client.get("/api/health").status_code == 200

    def test_docs_is_exempt(self, client: TestClient):
        for _ in range(20):
            # /docs may 404 but must never be 429
            assert client.get("/docs").status_code != 429

    def test_non_api_paths_are_passed_through(self):
        app = _create_app(user_max=1, unauth_max=1, auth_max=1, window=60)
        with TestClient(app) as c:
            for _ in range(5):
                assert c.get("/other").status_code == 200


class TestUnauthenticatedIpBucket:
    def test_blocks_after_unauth_max(self, client: TestClient):
        for _ in range(5):
            assert client.get("/api/passwords").status_code == 200
        r = client.get("/api/passwords")
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_headers_on_success(self, client: TestClient):
        r = client.get("/api/passwords")
        assert r.status_code == 200
        assert r.headers["X-RateLimit-Limit"] == "5"
        assert "X-RateLimit-Remaining" in r.headers

    def test_retry_after_on_429(self, client: TestClient):
        for _ in range(5):
            client.get("/api/passwords")
        r = client.get("/api/passwords")
        assert r.status_code == 429
        assert int(r.headers["Retry-After"]) > 0


class TestAuthenticatedUserBucket:
    def test_authenticated_user_uses_user_bucket_not_ip_bucket(self):
        """NAT scenario: two users on the same IP each get their own bucket."""
        user_a = "00000000-0000-0000-0000-000000000001"
        user_b = "00000000-0000-0000-0000-000000000002"
        resolver = _FakePrincipalResolver()
        resolver.register("token-a", user_a)
        resolver.register("token-b", user_b)

        # unauth_max=2 would break this test if the IP bucket were consulted for authed users
        app = _create_app(user_max=3, unauth_max=2, auth_max=100, principal_resolver=resolver)

        with TestClient(app) as c_a, TestClient(app) as c_b:
            c_a.cookies.set("access_token", "token-a")
            c_b.cookies.set("access_token", "token-b")
            # Same IP for both (TestClient uses 127.0.0.1 by default)
            for _ in range(3):
                assert c_a.get("/api/passwords").status_code == 200
            assert c_a.get("/api/passwords").status_code == 429

            # User B's bucket is untouched even though IP is shared
            for _ in range(3):
                assert c_b.get("/api/passwords").status_code == 200
            assert c_b.get("/api/passwords").status_code == 429

    def test_unauthenticated_requests_use_ip_bucket(self):
        app = _create_app(user_max=100, unauth_max=3, auth_max=100, principal_resolver=_FakePrincipalResolver())
        with TestClient(app) as c:
            for _ in range(3):
                assert c.get("/api/passwords").status_code == 200
            assert c.get("/api/passwords").status_code == 429

    def test_invalid_token_falls_back_to_ip_bucket(self):
        app = _create_app(user_max=100, unauth_max=3, auth_max=100, principal_resolver=_FakePrincipalResolver())
        with TestClient(app) as c:
            c.cookies.set("access_token", "not-a-real-token")
            for _ in range(3):
                assert c.get("/api/passwords").status_code == 200
            assert c.get("/api/passwords").status_code == 429


class TestAuthRouteFloor:
    def test_auth_route_floor_blocks_regardless_of_principal(self, client: TestClient):
        """auth_max=3 → 4th login must 429 even though user/unauth max are higher."""
        for _ in range(3):
            r = client.post("/api/auth/login")
            assert r.status_code == 401  # failed creds (the stub returns 401)
        assert client.post("/api/auth/login").status_code == 429

    def test_auth_floor_applies_to_credential_accepting_routes_only(self):
        """auth_max=3 routes: login, register-admin, refresh-token, sso/callback.
        Read-only sso routes (url, is-configured) must NOT consume the auth bucket."""
        # unauth_max is set high so the principal bucket doesn't interfere with this assertion.
        app = _create_app(user_max=100, unauth_max=100, auth_max=3, window=60)
        with TestClient(app) as c:
            # Exhaust the auth floor via login
            for _ in range(3):
                c.post("/api/auth/login")
            assert c.post("/api/auth/login").status_code == 429

            # Read-only sso routes are unaffected (they still consume the principal bucket
            # but not the auth floor, so with unauth_max=100 they return 200).
            for _ in range(5):
                assert c.get("/api/auth/sso/url").status_code == 200
                assert c.get("/api/auth/sso/is-configured").status_code == 200

    def test_auth_floor_applies_to_refresh_and_sso_callback(self):
        app = _create_app(user_max=100, unauth_max=100, auth_max=2, window=60)
        with TestClient(app) as c:
            # Any combination of credential-accepting routes drains the single floor
            assert c.post("/api/auth/refresh-token").status_code == 200
            assert c.get("/api/auth/sso/callback").status_code == 200
            # Third attempt hits the floor
            assert c.post("/api/auth/login").status_code == 429

    def test_auth_floor_and_principal_bucket_both_consumed_on_auth_routes(self):
        """A login also consumes the principal (IP or user) bucket."""
        app = _create_app(user_max=100, unauth_max=2, auth_max=100, login_status_code=401)
        with TestClient(app) as c:
            # 2 logins drain the unauth IP bucket
            for _ in range(2):
                assert c.post("/api/auth/login").status_code == 401
            # Unauth bucket exhausted → next IS blocked by principal bucket, not auth floor
            r = c.post("/api/auth/login")
            assert r.status_code == 429


class TestXForwardedFor:
    def test_unauthenticated_clients_on_different_xff_ips_get_separate_buckets(self):
        # Trust the TestClient peer ("testclient") so XFF is honored.
        app = _create_app(user_max=100, unauth_max=2, auth_max=100, trusted_proxies={"testclient"})
        with TestClient(app) as c:
            ip_a = {"X-Forwarded-For": "10.0.0.1"}
            ip_b = {"X-Forwarded-For": "10.0.0.2"}

            for _ in range(2):
                assert c.get("/api/passwords", headers=ip_a).status_code == 200
            assert c.get("/api/passwords", headers=ip_a).status_code == 429

            for _ in range(2):
                assert c.get("/api/passwords", headers=ip_b).status_code == 200

    def test_xff_is_honored_when_peer_is_trusted(self):
        """When the direct peer is trusted, the XFF header is honored and used as the client IP."""
        # TestClient's default peer is "testclient"; trust it explicitly.
        app = _create_app(user_max=100, unauth_max=2, auth_max=100, trusted_proxies={"testclient"})
        with TestClient(app) as c:
            for _ in range(2):
                assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 200
            assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 429
            # Different XFF → fresh bucket
            assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 200

    def test_xff_is_ignored_when_peer_is_not_trusted(self):
        """If the direct peer is not in trusted_proxies, the XFF header is
        discarded and all requests key on the peer — rotating XFF doesn't help."""
        app = _create_app(
            user_max=100,
            unauth_max=2,
            auth_max=100,
            trusted_proxies=set(),  # nothing trusted
        )
        with TestClient(app) as c:
            for _ in range(2):
                assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 200
            # 3rd request — XFF rotated but peer bucket is full
            assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 429


class TestConcurrency:
    def test_concurrent_auth_requests_are_counted_correctly(self):
        app = _create_app(user_max=100, unauth_max=100, auth_max=3, login_status_code=401)
        with TestClient(app) as c:

            def make_request():
                return c.post("/api/auth/login")

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in as_completed(futures)]

            allowed = [r for r in results if r.status_code != 429]
            limited = [r for r in results if r.status_code == 429]

            assert len(allowed) == 3
            assert len(limited) == 7

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from identity_access_management_context.application.gateways import Token
from identity_access_management_context.domain.exceptions import InvalidTokenException
from security.rate_limit_middleware import RateLimitMiddleware
from security.rate_limiter import InMemoryRateLimiter
from tests.shared_kernel.fakes import FakeTimeGateway


class _FakeTokenGateway:
    """Minimal token gateway for middleware unit tests."""

    def __init__(self) -> None:
        self._tokens: dict[str, Token] = {}
        self._raises: dict[str, Exception] = {}

    def register(self, token: str, user_id: str) -> None:
        self._tokens[token] = Token(value=token, user_id=UUID(user_id), email="", roles=[], claims={})

    def register_raising(self, token: str, exc: Exception) -> None:
        """Wire ``token`` so ``validate_token`` raises ``exc`` — lets us simulate
        both the domain InvalidTokenException path and arbitrary library errors."""
        self._raises[token] = exc

    def validate_token(self, token: str) -> Token | None:
        if token in self._raises:
            raise self._raises[token]
        return self._tokens.get(token)


def _create_app(
    *,
    user_max: int = 300,
    unauth_max: int = 30,
    auth_max: int = 100,
    vault_max: int = 10,
    sensitive_max: int = 1,
    sensitive_window: int = 60,
    one_time_link_max: int = 10,
    extension_pairing_max: int = 30,
    bearer_miss_max: int = 30,
    window: int = 60,
    login_status_code: int = 401,
    token_gateway: _FakeTokenGateway | None = None,
    trusted_proxies: set[str] | None = None,
    trusted_proxy_hops: int = 1,
    time_provider: FakeTimeGateway | None = None,
    session_maker=None,
) -> FastAPI:
    app = FastAPI(root_path="/api")

    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.time_provider = time_provider or FakeTimeGateway(datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))
    app.state.token_gateway = token_gateway
    app.state.rate_limit_user_max_requests = user_max
    app.state.rate_limit_unauth_max_requests = unauth_max
    app.state.rate_limit_auth_max_requests = auth_max
    app.state.rate_limit_vault_max_requests = vault_max
    app.state.rate_limit_vault_sensitive_max_requests = sensitive_max
    app.state.rate_limit_vault_sensitive_window_seconds = sensitive_window
    app.state.rate_limit_one_time_link_max_requests = one_time_link_max
    app.state.rate_limit_extension_pairing_max_requests = extension_pairing_max
    app.state.rate_limit_bearer_miss_max_requests = bearer_miss_max
    app.state.rate_limit_window_seconds = window
    if session_maker is not None:
        app.state.session_maker = session_maker
    app.state.rate_limit_trusted_proxies = trusted_proxies if trusted_proxies is not None else {"127.0.0.1", "::1"}
    app.state.rate_limit_trusted_proxy_hops = trusted_proxy_hops

    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health():
        return PlainTextResponse("ok")

    @app.get("/passwords")
    async def passwords():
        return PlainTextResponse("passwords")

    # The bearer-reachable routes, the only ones where the middleware is allowed
    # to spend a database lookup deciding which bucket to charge.
    @app.get("/extension/session")
    async def extension_session():
        return PlainTextResponse("session")

    @app.get("/passwords/list")
    async def passwords_list():
        return PlainTextResponse("list")

    @app.post("/passwords/list")
    async def passwords_list_post():
        return PlainTextResponse("list")

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
        return PlainTextResponse("sso-url", status_code=200)

    @app.get("/auth/sso/is-configured")
    async def sso_is_configured():
        return PlainTextResponse("configured", status_code=200)

    @app.get("/vault/status")
    async def vault_status():
        return PlainTextResponse("status", status_code=200)

    @app.post("/vault/unlock")
    async def vault_unlock():
        return PlainTextResponse("unlock", status_code=202)

    @app.post("/vault/setup")
    async def vault_setup():
        return PlainTextResponse("setup", status_code=201)

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


# ── Exempt paths ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/api/health",
        "/api/vault/status",
        "/api/auth/sso/url",
        "/api/auth/sso/is-configured",
    ],
)
def test_given_exempt_api_path_when_dispatching_should_pass_through(client: TestClient, path: str):
    """Frequently-polled endpoints must never trip a bucket, even under the
    tight fixture limits (unauth_max=5): the whole point of exempting them is
    that a normal UI can call them on every page without running out."""
    for _ in range(20):
        assert client.get(path).status_code != 429


def test_given_docs_or_openapi_path_when_dispatching_should_pass_through(client: TestClient):
    # Deployed paths are /api/docs and /api/openapi.json because FastAPI runs
    # with root_path="/api" and nginx preserves the prefix on proxy.
    for _ in range(20):
        assert client.get("/api/docs").status_code != 429
        assert client.get("/api/openapi.json").status_code != 429


def test_given_path_without_the_api_prefix_when_dispatching_should_still_rate_limit():
    """There is no "outside the API" once a root path is configured.

    Starlette routes `/passwords` and `/api/passwords` to the same handler
    when the app has root_path="/api", and an earlier version let the first
    form through untouched: every floor, login included, could be skipped by
    dropping the prefix on a direct connection to the backend port.
    """
    app = _create_app(user_max=1, unauth_max=1, auth_max=1, window=60)
    with TestClient(app) as c:
        assert c.get("/passwords").status_code == 200
        assert c.get("/passwords").status_code == 429
        # The two spellings share one bucket, since they are one route.
        assert c.get("/api/passwords").status_code == 429


def test_given_login_without_the_api_prefix_when_flooded_should_hit_the_auth_floor():
    app = _create_app(auth_max=2, unauth_max=100, window=60)
    with TestClient(app) as c:
        assert c.post("/auth/login").status_code == 401
        assert c.post("/auth/login").status_code == 401
        assert c.post("/auth/login").status_code == 429


# ── Unauthenticated IP bucket ─────────────────────────────────────────


def test_given_unauth_limit_reached_when_dispatching_should_block_caller(client: TestClient):
    for _ in range(5):
        assert client.get("/api/passwords").status_code == 200

    r = client.get("/api/passwords")

    assert r.status_code == 429
    assert "Too many requests" in r.json()["detail"]


def test_given_request_succeeds_when_dispatching_should_emit_ratelimit_headers(client: TestClient):
    r = client.get("/api/passwords")

    assert r.status_code == 200
    assert r.headers["X-RateLimit-Limit"] == "5"
    assert "X-RateLimit-Remaining" in r.headers


def test_given_request_blocked_when_dispatching_should_emit_retry_after(client: TestClient):
    for _ in range(5):
        client.get("/api/passwords")

    r = client.get("/api/passwords")

    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0


# ── Authenticated user bucket ─────────────────────────────────────────


def test_given_valid_access_token_when_dispatching_should_use_per_user_bucket():
    user_id = "00000000-0000-0000-0000-000000000001"
    gateway = _FakeTokenGateway()
    gateway.register("token-a", user_id)
    app = _create_app(user_max=3, unauth_max=100, auth_max=100, token_gateway=gateway)

    with TestClient(app) as c:
        c.cookies.set("access_token", "token-a")
        for _ in range(3):
            assert c.get("/api/passwords").status_code == 200
        r = c.get("/api/passwords")

    assert r.status_code == 429


def test_given_shared_ip_when_dispatching_should_isolate_user_buckets():
    """NAT regression: two users on the same IP each get their own bucket."""
    user_a = "00000000-0000-0000-0000-000000000001"
    user_b = "00000000-0000-0000-0000-000000000002"
    gateway = _FakeTokenGateway()
    gateway.register("token-a", user_a)
    gateway.register("token-b", user_b)
    app = _create_app(user_max=3, unauth_max=2, auth_max=100, token_gateway=gateway)

    with TestClient(app) as c_a, TestClient(app) as c_b:
        c_a.cookies.set("access_token", "token-a")
        c_b.cookies.set("access_token", "token-b")
        for _ in range(3):
            assert c_a.get("/api/passwords").status_code == 200
        assert c_a.get("/api/passwords").status_code == 429

        for _ in range(3):
            assert c_b.get("/api/passwords").status_code == 200
        assert c_b.get("/api/passwords").status_code == 429


def test_given_unknown_token_when_dispatching_should_fall_back_to_ip_bucket():
    app = _create_app(user_max=100, unauth_max=3, auth_max=100, token_gateway=_FakeTokenGateway())
    with TestClient(app) as c:
        c.cookies.set("access_token", "not-a-real-token")
        for _ in range(3):
            assert c.get("/api/passwords").status_code == 200
        r = c.get("/api/passwords")

    assert r.status_code == 429


def test_given_access_token_raises_invalid_token_when_dispatching_should_fall_back_silently(
    caplog: pytest.LogCaptureFixture,
):
    """Domain-level InvalidTokenException is the *expected* bad-token signal.
    The middleware must bucket as anonymous without logging at WARNING — otherwise
    every expired-cookie user generates an alert."""
    gateway = _FakeTokenGateway()
    gateway.register_raising("expired-token", InvalidTokenException())
    app = _create_app(user_max=100, unauth_max=3, auth_max=100, token_gateway=gateway)

    with caplog.at_level("WARNING", logger="security.rate_limit_middleware"):
        with TestClient(app) as c:
            c.cookies.set("access_token", "expired-token")
            for _ in range(3):
                assert c.get("/api/passwords").status_code == 200
            r = c.get("/api/passwords")

    assert r.status_code == 429
    assert not any("Token gateway" in rec.getMessage() for rec in caplog.records), (
        "InvalidTokenException must be treated as expected and MUST NOT log at WARNING"
    )


def test_given_access_token_raises_unexpected_error_when_dispatching_should_fall_back_and_log_warning(
    caplog: pytest.LogCaptureFixture,
):
    """A non-InvalidTokenException (library bug, JWT secret rotation mishap, UUID
    parse failure) is an operational signal. The middleware must still fail
    closed to IP keying so the request isn't served unauthenticated at the
    user-bucket rate, AND must log at WARNING so SRE sees the regression."""
    gateway = _FakeTokenGateway()
    gateway.register_raising("buggy-token", RuntimeError("jwt library blew up"))
    app = _create_app(user_max=100, unauth_max=3, auth_max=100, token_gateway=gateway)

    with caplog.at_level("WARNING", logger="security.rate_limit_middleware"):
        with TestClient(app) as c:
            c.cookies.set("access_token", "buggy-token")
            for _ in range(3):
                assert c.get("/api/passwords").status_code == 200
            r = c.get("/api/passwords")

    assert r.status_code == 429, "Must still fall back to the IP bucket, not 500"
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING" and "Token gateway" in rec.getMessage()]
    assert warnings, "Unexpected token-gateway errors must surface at WARNING"
    assert warnings[0].exc_info is not None, "WARNING must include exc_info for Sentry grouping"


# ── Vault-mutation floor (per-IP) ─────────────────────────────────────


def test_given_vault_unlock_flood_when_dispatching_should_apply_vault_floor():
    # /unlock is not a "sensitive op" (no global throttle); only the per-IP floor applies.
    app = _create_app(user_max=100, unauth_max=100, vault_max=3, window=60)
    with TestClient(app) as c:
        for _ in range(3):
            assert c.post("/api/vault/unlock", json={"shares": ["x"]}).status_code == 202
        assert c.post("/api/vault/unlock", json={"shares": ["x"]}).status_code == 429


def test_given_vault_status_when_flooded_should_stay_exempt():
    app = _create_app(user_max=100, unauth_max=100, vault_max=1, window=60)
    with TestClient(app) as c:
        for _ in range(5):
            assert c.get("/api/vault/status").status_code == 200


# ── Global destructive-op throttle (setup, once per window) ───


def test_given_setup_second_call_within_window_should_hit_global_throttle():
    app = _create_app(user_max=100, unauth_max=100, vault_max=100, sensitive_max=1, sensitive_window=60)
    with TestClient(app) as c:
        assert c.post("/api/vault/setup", json={"nb_shares": 3, "threshold": 2}).status_code == 201
        assert c.post("/api/vault/setup", json={"nb_shares": 3, "threshold": 2}).status_code == 429


def test_given_setup_throttle_is_global_across_ips():
    # A single shared bucket: a second setup from a DIFFERENT IP is still throttled,
    # so rotating IPs does not bypass the once-per-window limit.
    app = _create_app(user_max=100, unauth_max=100, vault_max=100, sensitive_max=1, trusted_proxies={"testclient"})
    with TestClient(app) as c:
        body = {"nb_shares": 3, "threshold": 2}
        assert c.post("/api/vault/setup", json=body, headers={"X-Forwarded-For": "203.0.113.1"}).status_code == 201
        assert c.post("/api/vault/setup", json=body, headers={"X-Forwarded-For": "203.0.113.2"}).status_code == 429


def test_given_unlock_when_flooded_should_not_consume_global_throttle():
    # Submitting shares (the anonymous multi-party path) must never be throttled by
    # the destructive-op bucket.
    app = _create_app(user_max=100, unauth_max=100, vault_max=100, sensitive_max=1)
    with TestClient(app) as c:
        for _ in range(5):
            assert c.post("/api/vault/unlock", json={"shares": ["x"]}).status_code == 202


# ── Auth-route floor (login only) ─────────────────────────────────────


def test_given_login_path_when_dispatching_should_apply_auth_floor(client: TestClient):
    for _ in range(3):
        r = client.post("/api/auth/login")
        assert r.status_code == 401  # stub returns 401

    r = client.post("/api/auth/login")

    assert r.status_code == 429


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/auth/register-admin"),
        ("post", "/api/auth/refresh-token"),
        ("get", "/api/auth/sso/callback"),
    ],
)
def test_given_non_login_auth_path_when_dispatching_should_not_consume_auth_floor(method: str, path: str):
    """The auth-route floor is narrow by design: only /api/auth/login trips it."""
    app = _create_app(user_max=100, unauth_max=100, auth_max=2, window=60)
    with TestClient(app) as c:
        for _ in range(5):
            r = getattr(c, method)(path)
            assert r.status_code != 429, f"{method.upper()} {path} unexpectedly hit the auth floor"

        for _ in range(2):
            assert c.post("/api/auth/login").status_code == 401
        assert c.post("/api/auth/login").status_code == 429


def test_given_principal_bucket_exhausted_when_logging_in_should_429_even_when_auth_floor_has_capacity():
    """Login requests consume the principal (unauth/IP) bucket in addition to
    the auth floor. With a tight unauth bucket and a roomy auth floor, the
    principal bucket must still catch the third request — otherwise a flood on
    /auth/login could starve every other /api/* call from the same IP."""
    app = _create_app(user_max=100, unauth_max=2, auth_max=100, login_status_code=401)
    with TestClient(app) as c:
        for _ in range(2):
            assert c.post("/api/auth/login").status_code == 401
        r = c.post("/api/auth/login")

    assert r.status_code == 429


def test_given_successful_login_when_auth_floor_exhausted_should_429_even_when_principal_bucket_has_capacity():
    """The counterpart to the test above: a genuinely successful login
    (status 200) still consumes the auth floor. With a tight auth_max and a
    roomy unauth bucket, the third successful login must be refused by the
    floor — proving the floor is not bypassed when the endpoint returns 2xx."""
    app = _create_app(user_max=100, unauth_max=100, auth_max=2, login_status_code=200)
    with TestClient(app) as c:
        for _ in range(2):
            assert c.post("/api/auth/login").status_code == 200
        r = c.post("/api/auth/login")

    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0


# ── X-Forwarded-For ───────────────────────────────────────────────────


def test_given_trusted_peer_when_dispatching_should_honor_xff():
    """TestClient connects as 'testclient', so mark it as a trusted proxy."""
    app = _create_app(user_max=100, unauth_max=2, auth_max=100, trusted_proxies={"testclient"})
    with TestClient(app) as c:
        for _ in range(2):
            assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 200
        assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 429
        assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 200


def test_given_untrusted_peer_when_dispatching_should_ignore_xff():
    """With no trusted proxies, XFF is discarded and all traffic keys on the TCP peer."""
    app = _create_app(user_max=100, unauth_max=2, auth_max=100, trusted_proxies=set())
    with TestClient(app) as c:
        for _ in range(2):
            assert c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 200
        r = c.get("/api/passwords", headers={"X-Forwarded-For": "203.0.113.10"})

    assert r.status_code == 429


# ── Concurrency ───────────────────────────────────────────────────────


# ── Defensive app.state validation ────────────────────────────────────


@pytest.mark.parametrize(
    "missing_key",
    [
        "rate_limiter",
        "rate_limit_user_max_requests",
        "rate_limit_unauth_max_requests",
        "rate_limit_auth_max_requests",
        "rate_limit_window_seconds",
        "rate_limit_trusted_proxies",
        "rate_limit_trusted_proxy_hops",
        "time_provider",
    ],
)
def test_given_app_state_missing_required_key_when_dispatching_should_log_critical_and_500(
    caplog: pytest.LogCaptureFixture, missing_key: str
):
    """If a future refactor renames an app.state attr and forgets one call site,
    EVERY /api/* request would generate a generic 500 — no dedicated signal
    distinguishes "rate limiter misconfigured" from "some other 500". Pin the
    CRITICAL log for every required key so a refactor that moves one read
    outside the try/except is caught here rather than at runtime."""
    app = _create_app(user_max=10, unauth_max=5, auth_max=3, window=60)
    delattr(app.state, missing_key)

    with caplog.at_level("CRITICAL", logger="security.rate_limit_middleware"):
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/api/passwords")

    assert r.status_code >= 500, f"Missing {missing_key} must fail-closed, not silently pass traffic"
    critical = [rec for rec in caplog.records if rec.levelname == "CRITICAL"]
    assert critical, f"Missing {missing_key} must log at CRITICAL so ops can alert specifically on it"
    msg = critical[0].getMessage().lower()
    assert "misconfigured" in msg or "rate_limit" in msg


def test_given_concurrent_requests_on_shared_bucket_when_dispatching_should_serialize_correctly():
    app = _create_app(user_max=100, unauth_max=100, auth_max=3, login_status_code=401)
    with TestClient(app) as c:

        def _post():
            return c.post("/api/auth/login")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_post) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

    allowed = [r for r in results if r.status_code != 429]
    limited = [r for r in results if r.status_code == 429]

    assert len(allowed) == 3
    assert len(limited) == 7


# ---------------------------------------------------------------------------
# Anonymous floors that replace the principal bucket
# ---------------------------------------------------------------------------


def _create_app_with_pairing_routes(**kwargs) -> FastAPI:
    app = _create_app(**kwargs)

    @app.post("/extension/device")
    async def register_device():
        return PlainTextResponse("registered")

    @app.post("/extension/device/exchange")
    async def exchange_device():
        return PlainTextResponse("pending")

    @app.post("/one-time-links/consume")
    async def consume_link():
        return PlainTextResponse("consumed")

    return app


def test_should_charge_pairing_polls_to_their_own_floor_and_nowhere_else():
    """Two colleagues pairing behind one NAT must not lock out a third.

    The floor existed, but the request fell through to the anonymous bucket
    afterwards, so every poll spent both. With a poll every five seconds per
    device, two devices plus their registrations reached 26 of the 30 shared
    requests per minute, and the next colleague on that address got 429s on
    the whole API.
    """
    app = _create_app_with_pairing_routes(unauth_max=2, extension_pairing_max=100)
    with TestClient(app) as c:
        for _ in range(10):
            assert c.post("/api/extension/device/exchange").status_code == 200

        # The anonymous bucket is untouched: two ordinary requests still pass.
        assert c.get("/api/passwords").status_code == 200
        assert c.get("/api/passwords").status_code == 200
        assert c.get("/api/passwords").status_code == 429


def test_should_refuse_pairing_polls_past_their_floor_whatever_the_anonymous_bucket_holds():
    app = _create_app_with_pairing_routes(unauth_max=100, extension_pairing_max=3)
    with TestClient(app) as c:
        for _ in range(3):
            assert c.post("/api/extension/device").status_code == 200
        response = c.post("/api/extension/device")

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Limit"] == "3"


def test_should_report_the_floor_in_the_headers_of_a_pairing_response():
    app = _create_app_with_pairing_routes(unauth_max=100, extension_pairing_max=5)
    with TestClient(app) as c:
        response = c.post("/api/extension/device")

    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"


def test_should_charge_one_time_link_redemptions_to_their_own_floor_and_nowhere_else():
    app = _create_app_with_pairing_routes(unauth_max=1, one_time_link_max=100)
    with TestClient(app) as c:
        for _ in range(5):
            assert c.post("/api/one-time-links/consume").status_code == 200
        assert c.get("/api/passwords").status_code == 200


# ---------------------------------------------------------------------------
# Extension bearer keying
#
# The middleware reads the database to decide which bucket an extension belongs
# to. That read happens before any bucket is consulted, on a request whose
# credential may be worthless, so these tests pin both halves of the contract:
# a paired extension really does get its own bucket, and nobody else can buy
# database work with a made-up token.
# ---------------------------------------------------------------------------


class _CountingSessionMaker:
    """A session_maker that records checkouts and serves one known token hash."""

    def __init__(self, known_hash: str | None = None, user_id: str | None = None, active: bool = True):
        self.checkouts = 0
        self._known_hash = known_hash
        self._user_id = user_id
        self._active = active

    def __call__(self):
        self.checkouts += 1
        return _FakeSession(self._known_hash, self._user_id, self._active)


class _FakeSession:
    def __init__(self, known_hash, user_id, active):
        self._known_hash = known_hash
        self._user_id = user_id
        self._active = active

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def exec(self, statement):
        """Answer the repository's SELECT without a database.

        The middleware builds a real SqlExtensionTokenRepository, so the fake
        has to sit one layer lower, at the session. `first()` is the only
        accessor `get_by_token_hash` uses.
        """
        return _FakeResult(self._row_for(statement))

    def _row_for(self, statement):
        if self._known_hash is None:
            return None
        # The hash is bound into the statement's parameters; comparing the
        # rendered SQL is enough to tell "the token we know" from any other.
        if self._known_hash not in str(statement.compile(compile_kwargs={"literal_binds": True})):
            return None
        return _FakeTokenRow(self._user_id, self._active)


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeTokenRow:
    def __init__(self, user_id, active):
        self.id = UUID("11111111-1111-1111-1111-111111111111")
        self.user_id = UUID(user_id)
        self.token_hash = ""
        self.device_name = "Chrome"
        self.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        self.expires_at = datetime(2026, 2, 1, tzinfo=UTC) if active else datetime(2026, 1, 1, tzinfo=UTC)
        self.last_used_at = None
        self.revoked_at = None if active else datetime(2026, 1, 1, tzinfo=UTC)
        self.created_from_ip = None


_VALID_TOKEN = "v" * 43
_UNKNOWN_TOKEN = "u" * 43
_USER_ID = "22222222-2222-2222-2222-222222222222"


def _hash_of(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def test_should_key_an_extension_to_its_user_when_it_sends_a_bearer_and_no_cookie():
    """The whole point of bearer keying, and it was dead.

    An extension never sends a cookie: they are SameSite=strict. A version of
    _resolve_principal that returned the IP principal as soon as the cookie was
    absent made the bearer branch unreachable for its only caller, leaving every
    extension in the shared anonymous bucket, which is what it exists to avoid.
    """
    maker = _CountingSessionMaker(known_hash=_hash_of(_VALID_TOKEN), user_id=_USER_ID)
    app = _create_app(user_max=5, unauth_max=2, session_maker=maker)

    with TestClient(app) as c:
        responses = [
            c.get("/api/extension/session", headers={"Authorization": f"Bearer {_VALID_TOKEN}"}) for _ in range(4)
        ]

    # Four requests with an anonymous limit of two: keyed on the IP they would
    # have been refused, keyed on the user they all pass.
    assert [r.status_code for r in responses] == [200, 200, 200, 200]
    # And only the first one paid for a lookup; BearerPrincipalCache answered
    # the rest, which is the difference between one query per extension request
    # and one per token per minute.
    assert maker.checkouts == 1


def test_should_not_touch_the_database_when_a_bearer_reaches_a_route_it_cannot_authenticate():
    """A bearer on any other route can only ever end in a 401.

    Resolving it there is a connection checkout plus a SELECT bought by an
    anonymous caller, on every request, including the ones already over their
    limit. A junk cookie is what used to make this reachable.
    """
    maker = _CountingSessionMaker()
    app = _create_app(unauth_max=3, session_maker=maker, token_gateway=_FakeTokenGateway())

    with TestClient(app) as c:
        for _ in range(6):
            c.post(
                "/api/auth/register-admin",
                headers={"Authorization": f"Bearer {_UNKNOWN_TOKEN}", "Cookie": "access_token=garbage"},
            )

    assert maker.checkouts == 0


def test_should_not_touch_the_database_when_a_bearer_arrives_on_a_mutating_request():
    """BearerReadOnlyMiddleware 403s this, but it runs LATER.

    main.py adds the rate limiter last, so it runs first, and without a method
    check of its own it would pay for the lookup before the read-only guard
    ever sees the request.
    """
    maker = _CountingSessionMaker()
    app = _create_app(session_maker=maker)

    with TestClient(app) as c:
        for _ in range(4):
            c.post("/api/passwords/list", headers={"Authorization": f"Bearer {_UNKNOWN_TOKEN}"})

    assert maker.checkouts == 0


def test_should_stop_querying_when_a_caller_spends_its_budget_of_failed_lookups():
    maker = _CountingSessionMaker()
    app = _create_app(unauth_max=1000, bearer_miss_max=3, session_maker=maker)

    with TestClient(app) as c:
        for _ in range(10):
            c.get("/api/passwords/list", headers={"Authorization": f"Bearer {_UNKNOWN_TOKEN}"})

    # Three misses are charged, the fourth request finds the budget already
    # spent and skips the lookup entirely. Without the budget this is 10.
    assert maker.checkouts == 3


def test_should_still_key_a_working_extension_when_a_neighbour_spends_the_miss_budget():
    """The guard must not become a sharper attack than the one it prevents.

    The budget is charged per address, so somebody guessing tokens from behind
    the same NAT spends it for everyone there. Without the cache being consulted
    first, that would push a colleague's working extension into the anonymous
    bucket the attacker has just filled: a targeted denial of service, handed
    out by the very guard meant to bound database work.
    """
    maker = _CountingSessionMaker(known_hash=_hash_of(_VALID_TOKEN), user_id=_USER_ID)
    app = _create_app(user_max=10, unauth_max=2, bearer_miss_max=2, session_maker=maker)

    with TestClient(app) as c:
        # The extension is in use, so its token is known.
        assert c.get("/api/extension/session", headers={"Authorization": f"Bearer {_VALID_TOKEN}"}).status_code == 200

        # A neighbour on the same address burns the miss budget.
        for _ in range(5):
            c.get("/api/passwords/list", headers={"Authorization": f"Bearer {_UNKNOWN_TOKEN}"})

        responses = [
            c.get("/api/extension/session", headers={"Authorization": f"Bearer {_VALID_TOKEN}"}) for _ in range(4)
        ]

    assert [r.status_code for r in responses] == [200, 200, 200, 200]


def test_should_fall_back_to_ip_keying_when_a_first_contact_lands_on_a_spent_budget():
    """The residual, stated rather than hidden.

    The cache can only protect a token it has seen. An extension pairing for the
    very first time while an attack is under way from the same address spends
    that window in the anonymous bucket. It recovers on its own once the budget
    refills, and this is the price of never letting an unknown token buy a query
    once the budget is gone.
    """
    maker = _CountingSessionMaker(known_hash=_hash_of(_VALID_TOKEN), user_id=_USER_ID)
    app = _create_app(user_max=10, unauth_max=2, bearer_miss_max=2, session_maker=maker)

    with TestClient(app) as c:
        for _ in range(5):
            c.get("/api/passwords/list", headers={"Authorization": f"Bearer {_UNKNOWN_TOKEN}"})

        first_contact = c.get("/api/extension/session", headers={"Authorization": f"Bearer {_VALID_TOKEN}"})

    assert first_contact.status_code == 429
    # Two misses charged, then nothing: the unknown token stopped costing
    # queries, and the valid one was never looked up either.
    assert maker.checkouts == 2

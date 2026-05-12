"""
Complete End-to-End Rate Limiting Workflow.

Rate limiting is a cross-cutting transport concern with no owning domain,
so it keeps its own workflow file. Every phase below observes HTTP behavior
only — no mocks, no fake gateway swaps. Reconstructing ``InMemoryRateLimiter()``
between runs is state cleanup, not mocking.

Covered phases:
1. Unauthenticated IP bucket blocks after ``unauth_max`` requests.
2. The auth-route floor applies to ``/api/auth/login`` only — other
   non-exempt /auth/* endpoints fall through to the principal bucket.
3. Exempt endpoints (health, vault/status, sso/url, sso/is-configured) are
   never rate-limited — these are routine per-page / pre-login polls.
4. X-Forwarded-For isolates buckets when the TCP peer is trusted.
"""

import pytest
from conftest import CsrfTestClient

from main import app
from security.rate_limiter import InMemoryRateLimiter


@pytest.fixture
def rate_limited_client(database, env_vars):
    with CsrfTestClient(app) as client:
        # Override limits on the live app state so phases trip deterministically.
        app.state.rate_limit_user_max_requests = 50
        app.state.rate_limit_unauth_max_requests = 5
        app.state.rate_limit_auth_max_requests = 3
        app.state.rate_limit_window_seconds = 60
        app.state.rate_limit_trusted_proxies = {"testclient"}
        app.state.rate_limit_trusted_proxy_hops = 1
        app.state.rate_limiter = InMemoryRateLimiter()
        yield client


def test_complete_rate_limiting_workflow(rate_limited_client: CsrfTestClient):
    print("\n" + "=" * 80)
    print("🚀 STARTING COMPLETE RATE LIMITING WORKFLOW TEST")
    print("=" * 80)

    rate_limited_client.disable_auto_csrf()

    # =========================================================================
    # PHASE 1: Unauthenticated IP bucket
    # =========================================================================
    print("\n📝 PHASE 1: Unauthenticated IP bucket")
    print("=" * 80)

    # /api/auth/refresh-token is rate-limited, unauthenticated (returns 401
    # without a refresh cookie), and stateless — a good target for probing
    # the unauth bucket boundary.
    for i in range(5):
        r = rate_limited_client.post("/api/auth/refresh-token")
        assert r.status_code != 429, f"Blocked too early on request {i + 1}"
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers

    r = rate_limited_client.post("/api/auth/refresh-token")
    assert r.status_code == 429
    assert "Too many requests" in r.json()["detail"]
    assert int(r.headers["Retry-After"]) > 0
    print("✅ 6th request correctly returns 429 with Retry-After")

    app.state.rate_limiter = InMemoryRateLimiter()

    # =========================================================================
    # PHASE 2: Auth-route floor on /api/auth/login only
    # =========================================================================
    print("\n🔒 PHASE 2: Auth-route floor applies to login only")
    print("=" * 80)

    for _ in range(3):
        r = rate_limited_client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
        assert r.status_code != 429

    r = rate_limited_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    print("✅ Auth floor trips on 4th login")

    # Reset the rate limiter and prove a non-login /auth/* endpoint
    # (/auth/refresh-token) doesn't share the auth floor. With auth_max=3
    # exhausted on login above, a fresh limiter + 4 refresh-token posts
    # stay under unauth_max=5 — the only thing that could block is an
    # auth-floor leak, which we're proving is absent.
    app.state.rate_limiter = InMemoryRateLimiter()
    for _ in range(4):
        assert rate_limited_client.post("/api/auth/refresh-token").status_code != 429
    print("✅ /api/auth/refresh-token does not consume the auth floor")

    app.state.rate_limiter = InMemoryRateLimiter()

    # =========================================================================
    # PHASE 3: Exempt endpoints are never rate-limited
    # =========================================================================
    print("\n💚 PHASE 3: Exempt endpoints are never rate-limited")
    print("=" * 80)

    # /api/auth/sso/url isn't probed here because it raises 500 without SSO
    # configured (unrelated to rate limiting); the full exempt set is asserted
    # at the unit-test layer in TestExemptPaths.
    exempt_paths = [
        "/api/health",
        "/api/vault/status",
        "/api/auth/sso/is-configured",
    ]
    for path in exempt_paths:
        for _ in range(50):
            assert rate_limited_client.get(path).status_code != 429, f"{path} unexpectedly rate-limited"
    print(f"✅ 50 requests each for {len(exempt_paths)} exempt endpoints — none limited")

    app.state.rate_limiter = InMemoryRateLimiter()

    # =========================================================================
    # PHASE 4: X-Forwarded-For isolates buckets when peer is trusted
    # =========================================================================
    print("\n🌐 PHASE 4: XFF trust partitions buckets per real client IP")
    print("=" * 80)

    ip_a = {"X-Forwarded-For": "203.0.113.10"}
    ip_b = {"X-Forwarded-For": "203.0.113.20"}

    for _ in range(5):
        assert rate_limited_client.post("/api/auth/refresh-token", headers=ip_a).status_code != 429
    r = rate_limited_client.post("/api/auth/refresh-token", headers=ip_a)
    assert r.status_code == 429
    print("✅ IP-A exhausts its bucket at 5 requests")

    r = rate_limited_client.post("/api/auth/refresh-token", headers=ip_b)
    assert r.status_code != 429
    print("✅ IP-B still has its own fresh bucket")

    print("\n" + "=" * 80)
    print("🎊 COMPLETE RATE LIMITING WORKFLOW TEST PASSED")
    print("=" * 80 + "\n")

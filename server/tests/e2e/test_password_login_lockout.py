"""Integration test: login route short-circuits bcrypt during active lockout.

The inline lockout check in the login route must fire BEFORE the use case runs,
so a locked account's 401 response has the same latency as any other 401 (no
bcrypt verification). This test proves that invariant by observing
``password_hashing_gateway.verify`` is never called on a locked attempt.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from main import app
from security import InMemoryLoginLockout


@pytest.fixture
def client(database, env_vars):
    # TestClient's ``with`` block triggers the FastAPI lifespan, which is
    # where ``app.state.login_lockout`` gets installed. We must swap it
    # AFTER lifespan has run, otherwise the attribute doesn't exist yet.
    with TestClient(app) as c:
        original_lockout = app.state.login_lockout
        app.state.login_lockout = InMemoryLoginLockout(max_failures=3, lockout_seconds=300)
        # Relax middleware so we never see middleware 429s interfering with 401s.
        app.state.rate_limit_auth_max_requests = 10000
        app.state.rate_limit_unauth_max_requests = 10000
        app.state.rate_limit_user_max_requests = 10000
        app.state.rate_limiter.reset()
        try:
            yield c
        finally:
            app.state.login_lockout = original_lockout


class TestLoginRouteLockout:
    def test_fourth_failed_attempt_returns_locked_detail(self, client: TestClient):
        email = "lockme@example.com"
        for _ in range(3):
            r = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
            assert r.status_code == 401
            assert "locked" not in r.json()["detail"].lower()

        r = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        assert r.status_code == 401
        assert "locked" in r.json()["detail"].lower()
        assert int(r.headers["Retry-After"]) > 0

    def test_locked_email_does_not_invoke_password_verification(self, client: TestClient, monkeypatch):
        email = "timing@example.com"
        for _ in range(3):
            client.post("/api/auth/login", json={"email": email, "password": "wrong"})

        # Now the account is locked. Stub the password hashing gateway's verify;
        # a subsequent login attempt must NOT reach it.
        verify_mock = MagicMock(return_value=False)
        gateway = app.state.password_hashing_gateway
        monkeypatch.setattr(gateway, "verify", verify_mock)

        r = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        assert r.status_code == 401
        assert "locked" in r.json()["detail"].lower()
        assert verify_mock.call_count == 0, "Use case ran during lockout — inline check missed"

    def test_failures_on_different_emails_do_not_share_counter(self, client: TestClient):
        # 2 failures on each of two emails; neither should lock (threshold=3)
        for email in ("a@example.com", "b@example.com"):
            for _ in range(2):
                r = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
                assert "locked" not in r.json()["detail"].lower()

    def test_malformed_body_does_not_touch_lockout_state(self, client: TestClient):
        # Body missing required field — Pydantic 422, never reaches the handler
        r = client.post("/api/auth/login", json={"password": "wrong"})
        assert r.status_code == 422

        # A subsequent well-formed attempt behaves normally (not marked as locked).
        r = client.post("/api/auth/login", json={"email": "fresh@example.com", "password": "wrong"})
        assert r.status_code == 401
        assert "locked" not in r.json()["detail"].lower()

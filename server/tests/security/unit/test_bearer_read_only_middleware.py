"""The middleware-level belt on the bearer read-only rule.

Redundant with `ApiPrincipal.ensure_method_allowed` on purpose: CsrfMiddleware
only engages when a session cookie is present, so the whole bearer class sits
outside CSRF by construction. That is only safe while a bearer can never reach a
mutating route, and this restores that guarantee at the layer where the
invariant it replaces used to live.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from security import BearerReadOnlyMiddleware

MUTATING_METHODS = ["post", "put", "patch", "delete"]


def _client() -> TestClient:
    # No root_path: the paths below are declared in full, which is what the
    # middleware sees in `request.url.path` behind the real proxy.
    app = FastAPI()

    @app.get("/api/passwords/list")
    def list_passwords():
        return {"ok": True}

    @app.api_route("/api/passwords/{password_id}", methods=["POST", "PUT", "PATCH", "DELETE"])
    def mutate_password(password_id: str):
        return {"ok": True}

    @app.post("/api/extension/device")
    def register_device():
        return {"ok": True}

    @app.post("/public/thing")
    def public_thing():
        return {"ok": True}

    app.add_middleware(BearerReadOnlyMiddleware)
    return TestClient(app)


@pytest.mark.parametrize("method", MUTATING_METHODS)
def test_should_refuse_when_a_bearer_attempts_a_mutating_api_request(method: str):
    response = getattr(_client(), method)("/api/passwords/abc", headers={"Authorization": "Bearer some-token"})

    assert response.status_code == 403
    assert "read-only" in response.json()["detail"]


@pytest.mark.parametrize("scheme", ["Bearer", "bearer", "BEARER", "BeArEr"])
def test_should_refuse_whatever_the_case_of_the_scheme(scheme: str):
    # RFC 7235 makes the scheme case-insensitive, so a lowercase `bearer` must
    # not slip past.
    response = _client().post("/api/passwords/abc", headers={"Authorization": f"{scheme} some-token"})

    assert response.status_code == 403


def test_should_allow_a_bearer_to_read():
    response = _client().get("/api/passwords/list", headers={"Authorization": "Bearer some-token"})

    assert response.status_code == 200


@pytest.mark.parametrize("method", MUTATING_METHODS)
def test_should_allow_a_mutating_request_when_no_bearer_is_present(method: str):
    # Cookie-authenticated callers are untouched: this middleware only ever
    # looks at the Authorization header.
    response = getattr(_client(), method)("/api/passwords/abc")

    assert response.status_code == 200


def test_should_allow_the_anonymous_pairing_post_which_carries_no_bearer():
    response = _client().post("/api/extension/device")

    assert response.status_code == 200


def test_should_ignore_requests_outside_the_api_prefix():
    response = _client().post("/public/thing", headers={"Authorization": "Bearer some-token"})

    assert response.status_code == 200


def test_should_ignore_a_non_bearer_authorization_header():
    response = _client().post("/api/passwords/abc", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 200

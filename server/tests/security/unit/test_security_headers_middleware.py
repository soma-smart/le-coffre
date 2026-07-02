from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from security.security_headers_middleware import CONTENT_SECURITY_POLICY, SecurityHeadersMiddleware


def _build_app(**kwargs) -> FastAPI:
    app = FastAPI(**kwargs)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ok")
    async def ok():
        return PlainTextResponse("ok")

    return app


def test_given_response_when_dispatching_should_add_browser_security_headers():
    app = _build_app()

    with TestClient(app) as client:
        response = client.get("/ok")

    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    assert response.headers["X-XSS-Protection"] == "0"


def test_given_openapi_endpoint_when_dispatching_should_omit_csp_but_keep_other_headers():
    app = _build_app()

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_given_docs_endpoint_when_dispatching_should_omit_csp():
    app = _build_app()

    with TestClient(app) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers


def test_given_root_path_when_requesting_openapi_should_still_omit_csp():
    app = _build_app(root_path="/api")

    with TestClient(app) as client:
        response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers


def test_given_non_docs_route_when_dispatching_should_apply_csp():
    app = _build_app(root_path="/api")

    with TestClient(app) as client:
        response = client.get("/api/ok")

    assert response.status_code == 200
    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY

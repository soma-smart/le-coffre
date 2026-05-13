from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from security.security_headers_middleware import CONTENT_SECURITY_POLICY, SecurityHeadersMiddleware


def test_given_response_when_dispatching_should_add_browser_security_headers():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ok")
    async def ok():
        return PlainTextResponse("ok")

    with TestClient(app) as client:
        response = client.get("/ok")

    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    assert response.headers["X-XSS-Protection"] == "0"

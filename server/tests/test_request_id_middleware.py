import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared_kernel.adapters.primary.request_id_middleware import (
    RequestIdFilter,
    RequestIdMiddleware,
    _request_id_var,
)


@pytest.fixture
def app_with_middleware():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_request_id_middleware_generates_uuid_when_no_header(app_with_middleware):
    """When X-Request-ID is absent, the middleware must generate a UUID and return it."""
    import uuid

    with TestClient(app_with_middleware) as client:
        response = client.get("/ping")
    assert "x-request-id" in response.headers
    uuid.UUID(response.headers["x-request-id"])  # raises ValueError if not a valid UUID


def test_request_id_middleware_forwards_existing_id(app_with_middleware):
    """When X-Request-ID is present in the request, it must be echoed in the response."""
    with TestClient(app_with_middleware) as client:
        response = client.get("/ping", headers={"x-request-id": "my-trace-abc"})
    assert response.headers["x-request-id"] == "my-trace-abc"


def test_request_id_filter_injects_request_id_into_log_record():
    """RequestIdFilter must set record.request_id from the active ContextVar."""
    f = RequestIdFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    token = _request_id_var.set("req-xyz-123")
    try:
        f.filter(record)
    finally:
        _request_id_var.reset(token)
    assert record.request_id == "req-xyz-123"


def test_request_id_filter_uses_default_when_no_context():
    """Outside a request, RequestIdFilter must inject the default '-' value."""
    f = RequestIdFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    f.filter(record)
    assert record.request_id == "-"

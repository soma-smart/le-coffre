import logging
import os
import sys
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring import setup_monitoring, _UvicornAccessFilter


def _make_fresh_app() -> FastAPI:
    return FastAPI(root_path="/api")


# --- ENABLE_MONITORING=false ---


def test_setup_monitoring_disabled_by_env():
    """When ENABLE_MONITORING=false, no /metrics route must be mounted."""
    app = _make_fresh_app()
    with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
        setup_monitoring(app)

    routes = {r.path for r in app.routes}
    assert "/metrics" not in routes


def test_setup_monitoring_disabled_does_not_log_skipping(caplog):
    """When disabled by env var, no warning about missing deps should appear."""
    app = _make_fresh_app()
    with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
        with caplog.at_level(logging.INFO, logger="monitoring"):
            setup_monitoring(app)

    assert "Monitoring dependencies not installed" not in caplog.text


# --- Missing OTel dependencies ---


def test_setup_monitoring_without_dependencies_mounts_no_metrics_route():
    """When OTel packages are absent, no /metrics route must be mounted."""
    app = _make_fresh_app()

    otel_modules = [k for k in sys.modules if k.startswith("opentelemetry")]
    with patch.dict(sys.modules, {mod: None for mod in [
        "opentelemetry",
        "opentelemetry.instrumentation",
        "opentelemetry.instrumentation.fastapi",
        "opentelemetry.exporter",
        "opentelemetry.exporter.prometheus",
        "opentelemetry.sdk",
        "opentelemetry.sdk.metrics",
        "opentelemetry.sdk.metrics.export",
    ]}):
        setup_monitoring(app)

    routes = {r.path for r in app.routes}
    assert "/metrics" not in routes


def test_setup_monitoring_without_dependencies_logs_info(caplog):
    """When OTel packages are absent, an INFO message must be emitted."""
    app = _make_fresh_app()
    with patch.dict(sys.modules, {mod: None for mod in [
        "opentelemetry",
        "opentelemetry.instrumentation",
        "opentelemetry.instrumentation.fastapi",
        "opentelemetry.exporter",
        "opentelemetry.exporter.prometheus",
        "opentelemetry.sdk",
        "opentelemetry.sdk.metrics",
        "opentelemetry.sdk.metrics.export",
    ]}):
        with caplog.at_level(logging.INFO, logger="monitoring"):
            setup_monitoring(app)

    assert "Monitoring dependencies not installed" in caplog.text


# --- UvicornAccessFilter behaviour ---


def _make_record(method: str, path: str, status: int) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:12345", method, path, "1.1", status),
        exc_info=None,
    )


def test_filter_suppresses_health_regardless_of_monitoring():
    """Health check successes must always be suppressed."""
    f = _UvicornAccessFilter(monitoring_active=False)
    assert f.filter(_make_record("GET", "/api/health", 200)) is False


def test_filter_suppresses_metrics_when_monitoring_active():
    """/api/metrics successes must be suppressed when monitoring is active."""
    f = _UvicornAccessFilter(monitoring_active=True)
    assert f.filter(_make_record("GET", "/api/metrics", 200)) is False


def test_filter_does_not_suppress_metrics_when_monitoring_inactive():
    """/api/metrics must not be filtered when the endpoint does not exist."""
    f = _UvicornAccessFilter(monitoring_active=False)
    assert f.filter(_make_record("GET", "/api/metrics", 200)) is True


def test_filter_keeps_business_routes():
    """Business endpoint logs must never be filtered."""
    f = _UvicornAccessFilter(monitoring_active=True)
    assert f.filter(_make_record("GET", "/api/passwords/list", 200)) is True

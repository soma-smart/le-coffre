import logging
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi import FastAPI

from monitoring import setup_monitoring, _UvicornAccessFilter


def _make_fresh_app() -> FastAPI:
    return FastAPI(root_path="/api")


# --- Hard disable via ENABLE_MONITORING=false ---


def test_setup_monitoring_disabled_by_env_does_not_instrument():
    """When ENABLE_MONITORING=false, no OTel instrumentation must run."""
    app = _make_fresh_app()
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
            setup_monitoring(app)
    mock_configure.assert_not_called()


def test_setup_monitoring_disabled_does_not_log_skipping(caplog):
    """When disabled by env var, no message about missing deps should appear."""
    app = _make_fresh_app()
    with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
        with caplog.at_level(logging.INFO, logger="monitoring"):
            setup_monitoring(app)
    assert "Monitoring dependencies not installed" not in caplog.text


# --- No OTEL_EXPORTER_OTLP_ENDPOINT → no-op ---


def test_setup_monitoring_without_endpoint_is_noop():
    """Without OTEL_EXPORTER_OTLP_ENDPOINT, monitoring must be silent no-op."""
    app = _make_fresh_app()
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env.pop("ENABLE_MONITORING", None)
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, env, clear=True):
            setup_monitoring(app)
    mock_configure.assert_not_called()


def test_setup_monitoring_without_endpoint_emits_no_logs(caplog):
    """Without endpoint, no INFO/WARNING must be emitted."""
    app = _make_fresh_app()
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env.pop("ENABLE_MONITORING", None)
    with patch.dict(os.environ, env, clear=True):
        with caplog.at_level(logging.INFO, logger="monitoring"):
            setup_monitoring(app)
    assert caplog.text == ""


# --- Missing OTel dependencies when endpoint is set ---


_OTEL_MODULES = [
    "opentelemetry",
    "opentelemetry.instrumentation",
    "opentelemetry.instrumentation.fastapi",
    "opentelemetry.exporter",
    "opentelemetry.exporter.otlp",
    "opentelemetry.exporter.otlp.proto",
    "opentelemetry.exporter.otlp.proto.http",
    "opentelemetry.exporter.otlp.proto.http.metric_exporter",
    "opentelemetry.sdk",
    "opentelemetry.sdk.metrics",
    "opentelemetry.sdk.metrics.export",
    "opentelemetry.sdk.resources",
]


def test_setup_monitoring_without_dependencies_does_not_instrument(caplog):
    """When OTel packages are absent but endpoint is set, no instrumentation runs."""
    app = _make_fresh_app()
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch.dict(sys.modules, {mod: None for mod in _OTEL_MODULES}):
            with caplog.at_level(logging.INFO, logger="monitoring"):
                setup_monitoring(app)
    assert "Monitoring dependencies not installed" in caplog.text


def test_setup_monitoring_without_dependencies_logs_info(caplog):
    """When OTel packages are absent, an INFO message must be emitted."""
    app = _make_fresh_app()
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch.dict(sys.modules, {mod: None for mod in _OTEL_MODULES}):
            with caplog.at_level(logging.INFO, logger="monitoring"):
                setup_monitoring(app)
    assert "Monitoring dependencies not installed" in caplog.text


# --- ENABLE_MONITORING=true without endpoint ---


def test_setup_monitoring_enable_true_without_endpoint_is_noop():
    """When ENABLE_MONITORING=true but no endpoint, monitoring must be a silent no-op."""
    app = _make_fresh_app()
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env["ENABLE_MONITORING"] = "true"
    env.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, env, clear=True):
            setup_monitoring(app)
    mock_configure.assert_not_called()


def test_setup_monitoring_enable_true_without_endpoint_logs_warning(caplog):
    """When ENABLE_MONITORING=true but no endpoint, a WARNING must be emitted."""
    app = _make_fresh_app()
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env["ENABLE_MONITORING"] = "true"
    env.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    with patch.dict(os.environ, env, clear=True):
        with caplog.at_level(logging.WARNING, logger="monitoring"):
            setup_monitoring(app)
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in caplog.text


# --- Active monitoring with OTLP endpoint ---


def test_setup_monitoring_active_calls_configure_otel():
    """When endpoint is set and deps present, _configure_otel must be called."""
    app = _make_fresh_app()
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            with patch("monitoring._try_import_otel", return_value=True):
                setup_monitoring(app)
    mock_configure.assert_called_once()


def test_setup_monitoring_active_mounts_no_metrics_route():
    """OTLP mode must never mount a /metrics route."""
    app = _make_fresh_app()
    with patch("monitoring._configure_otel"):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            with patch("monitoring._try_import_otel", return_value=True):
                setup_monitoring(app)
    routes = {r.path for r in app.routes}
    assert "/metrics" not in routes


# --- UvicornAccessFilter unit behaviour ---


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
    """/api/metrics successes must be suppressed when monitoring_active=True."""
    f = _UvicornAccessFilter(monitoring_active=True)
    assert f.filter(_make_record("GET", "/api/metrics", 200)) is False


def test_filter_does_not_suppress_metrics_when_monitoring_inactive():
    """/api/metrics must pass through when monitoring is not active."""
    f = _UvicornAccessFilter(monitoring_active=False)
    assert f.filter(_make_record("GET", "/api/metrics", 200)) is True


def test_filter_keeps_business_routes():
    """Business endpoint logs must never be filtered."""
    f = _UvicornAccessFilter(monitoring_active=True)
    assert f.filter(_make_record("GET", "/api/passwords/list", 200)) is True

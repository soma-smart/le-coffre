import json
import logging
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi import FastAPI

from monitoring import JsonFormatter, setup_monitoring, _UvicornAccessFilter, setup_logging


@pytest.fixture
def app() -> FastAPI:
    return FastAPI(root_path="/api")


# --- Hard disable via ENABLE_MONITORING=false ---


def test_setup_monitoring_disabled_by_env_does_not_instrument(app):
    """When ENABLE_MONITORING=false, no OTel instrumentation must run."""
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
            setup_monitoring(app)
    mock_configure.assert_not_called()


def test_setup_monitoring_disabled_does_not_log_skipping(app, caplog):
    """When disabled by env var, no message about missing deps should appear."""
    with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
        with caplog.at_level(logging.INFO, logger="monitoring"):
            setup_monitoring(app)
    assert "Monitoring dependencies not installed" not in caplog.text


# --- No OTEL_EXPORTER_OTLP_ENDPOINT → no-op ---


def test_setup_monitoring_without_endpoint_is_noop(app):
    """Without OTEL_EXPORTER_OTLP_ENDPOINT, monitoring must be silent no-op."""
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env.pop("ENABLE_MONITORING", None)
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, env, clear=True):
            setup_monitoring(app)
    mock_configure.assert_not_called()


def test_setup_monitoring_without_endpoint_emits_no_logs(app, caplog):
    """Without endpoint, no INFO/WARNING must be emitted."""
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


def test_setup_monitoring_without_dependencies_does_not_instrument(app, caplog):
    """When OTel packages are absent but endpoint is set, no instrumentation runs."""
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch.dict(sys.modules, {mod: None for mod in _OTEL_MODULES}):
            with caplog.at_level(logging.INFO, logger="monitoring"):
                setup_monitoring(app)
    assert "Monitoring dependencies not installed" in caplog.text


def test_setup_monitoring_without_dependencies_logs_info(app, caplog):
    """When OTel packages are absent, an INFO message must be emitted."""
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch.dict(sys.modules, {mod: None for mod in _OTEL_MODULES}):
            with caplog.at_level(logging.INFO, logger="monitoring"):
                setup_monitoring(app)
    assert "Monitoring dependencies not installed" in caplog.text


# --- ENABLE_MONITORING=true without endpoint ---


def test_setup_monitoring_enable_true_without_endpoint_is_noop(app):
    """When ENABLE_MONITORING=true but no endpoint, monitoring must be a silent no-op."""
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env["ENABLE_MONITORING"] = "true"
    env.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, env, clear=True):
            setup_monitoring(app)
    mock_configure.assert_not_called()


def test_setup_monitoring_enable_true_without_endpoint_logs_warning(app, caplog):
    """When ENABLE_MONITORING=true but no endpoint, a WARNING must be emitted."""
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    env["ENABLE_MONITORING"] = "true"
    env.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    with patch.dict(os.environ, env, clear=True):
        with caplog.at_level(logging.WARNING, logger="monitoring"):
            setup_monitoring(app)
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in caplog.text


# --- Active monitoring with OTLP endpoint ---


def test_setup_monitoring_active_calls_configure_otel(app):
    """When endpoint is set and deps present, _configure_otel must be called."""
    with patch("monitoring._configure_otel") as mock_configure:
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            with patch("monitoring._try_import_otel", return_value=True):
                setup_monitoring(app)
    mock_configure.assert_called_once()


def test_setup_monitoring_active_mounts_no_metrics_route(app):
    """OTLP mode must never mount a /metrics route."""
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


def _make_application_record(level=logging.INFO, msg="hello world", name="src.main"):
    record = logging.LogRecord(
        name=name, level=level, pathname="", lineno=0,
        msg=msg, args=(), exc_info=None,
    )
    return record


def test_json_formatter_returns_valid_json():
    fmt = JsonFormatter()
    output = fmt.format(_make_application_record())
    parsed = json.loads(output)  # must not raise
    assert isinstance(parsed, dict)


def test_json_formatter_contains_required_fields():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_application_record()))
    assert {"timestamp", "level", "logger", "message"} <= parsed.keys()


def test_json_formatter_level_is_uppercase_string():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_application_record(level=logging.WARNING)))
    assert parsed["level"] == "WARNING"


def test_json_formatter_message_matches_record():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_application_record(msg="startup complete")))
    assert parsed["message"] == "startup complete"


def test_json_formatter_with_exc_info_includes_exception():
    fmt = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="src.main", level=logging.ERROR, pathname="", lineno=0,
            msg="something failed", args=(), exc_info=sys.exc_info(),
        )
        parsed = json.loads(fmt.format(record))
    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]


def test_json_formatter_handles_uvicorn_access_tuple_args():
    """Uvicorn access logs use tuple args — must not crash."""
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="uvicorn.access", level=logging.INFO, pathname="", lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:1234", "GET", "/api/passwords/list", "1.1", 200),
        exc_info=None,
    )
    output = fmt.format(record)
    parsed = json.loads(output)
    assert "200" in parsed["message"] or "/api/passwords/list" in parsed["message"]


def test_setup_logging_noop_when_log_format_not_set():
    """Without LOG_FORMAT, handlers must keep their original formatters."""
    access_logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    original_formatter = logging.Formatter()
    handler.setFormatter(original_formatter)
    access_logger.addHandler(handler)
    try:
        env = {k: v for k, v in os.environ.items() if k != "LOG_FORMAT"}
        with patch.dict(os.environ, env, clear=True):
            setup_logging()
        assert handler.formatter is original_formatter
    finally:
        access_logger.removeHandler(handler)


def test_setup_logging_noop_when_log_format_is_text():
    """LOG_FORMAT=text must be a no-op."""
    access_logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    original_formatter = logging.Formatter()
    handler.setFormatter(original_formatter)
    access_logger.addHandler(handler)
    try:
        with patch.dict(os.environ, {"LOG_FORMAT": "text"}):
            setup_logging()
        assert handler.formatter is original_formatter
    finally:
        access_logger.removeHandler(handler)


def test_setup_logging_installs_json_formatter_on_uvicorn_access():
    """LOG_FORMAT=json must install JsonFormatter on uvicorn.access handlers."""
    access_logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    access_logger.addHandler(handler)
    try:
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            setup_logging()
        assert isinstance(handler.formatter, JsonFormatter)
    finally:
        access_logger.removeHandler(handler)


def test_setup_logging_installs_json_formatter_on_uvicorn_error():
    """LOG_FORMAT=json must install JsonFormatter on uvicorn.error handlers."""
    error_logger = logging.getLogger("uvicorn.error")
    handler = logging.StreamHandler()
    error_logger.addHandler(handler)
    try:
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            setup_logging()
        assert isinstance(handler.formatter, JsonFormatter)
    finally:
        error_logger.removeHandler(handler)

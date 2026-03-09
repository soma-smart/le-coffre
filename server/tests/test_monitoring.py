import json
import logging
import os
import sys

import pytest

pytest.importorskip("opentelemetry")
from unittest.mock import MagicMock, patch

import opentelemetry.trace as otel_trace
from fastapi import FastAPI
from opentelemetry.trace import INVALID_SPAN_CONTEXT, NonRecordingSpan

from monitoring import JsonFormatter, _parse_resource_attributes, _UvicornAccessFilter, setup_logging, setup_monitoring


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


def test_setup_monitoring_without_dependencies_does_not_instrument(app, caplog):
    """When OTel packages are absent but endpoint is set, no instrumentation runs."""
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch("monitoring._OTEL_AVAILABLE", False):
            with caplog.at_level(logging.INFO, logger="monitoring"):
                setup_monitoring(app)
    assert "Monitoring dependencies not installed" in caplog.text


def test_setup_monitoring_without_dependencies_logs_info(app, caplog):
    """When OTel packages are absent, an INFO message must be emitted."""
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch("monitoring._OTEL_AVAILABLE", False):
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
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
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
            name="src.main",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="something failed",
            args=(),
            exc_info=sys.exc_info(),
        )
        parsed = json.loads(fmt.format(record))
    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]


def test_json_formatter_includes_extra_fields():
    """Extra fields passed via logger.info(..., extra={}) must appear in JSON output."""
    fmt = JsonFormatter()
    record = _make_application_record()
    record.password_id = "abc123"
    record.user_id = "user-42"
    parsed = json.loads(fmt.format(record))
    assert parsed["password_id"] == "abc123"
    assert parsed["user_id"] == "user-42"


def test_json_formatter_extra_fields_do_not_override_reserved_keys():
    """Extra fields must not be able to overwrite timestamp, level, logger, message."""
    fmt = JsonFormatter()
    record = _make_application_record(msg="real message")
    record.message = "injected"
    record.level = "INJECTED"
    parsed = json.loads(fmt.format(record))
    assert parsed["message"] == "real message"
    assert parsed["level"] == "INFO"


def test_json_formatter_handles_uvicorn_access_tuple_args():
    """Uvicorn access logs use tuple args — must not crash."""
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
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


# --- _parse_resource_attributes: Kubernetes downward API auto-detection ---


def test_parse_resource_attributes_empty_when_no_env_vars():
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("OTEL_RESOURCE_ATTRIBUTES", "POD_NAME", "NODE_NAME", "POD_NAMESPACE")
    }
    with patch.dict(os.environ, env, clear=True):
        assert _parse_resource_attributes() == {}


def test_parse_resource_attributes_maps_pod_name():
    with patch.dict(os.environ, {"POD_NAME": "le-coffre-backend-abc123"}, clear=False):
        result = _parse_resource_attributes()
    assert result.get("k8s.pod.name") == "le-coffre-backend-abc123"


def test_parse_resource_attributes_maps_node_name():
    with patch.dict(os.environ, {"NODE_NAME": "node-1"}, clear=False):
        result = _parse_resource_attributes()
    assert result.get("k8s.node.name") == "node-1"


def test_parse_resource_attributes_maps_pod_namespace():
    with patch.dict(os.environ, {"POD_NAMESPACE": "le-coffre"}, clear=False):
        result = _parse_resource_attributes()
    assert result.get("k8s.namespace.name") == "le-coffre"


def test_parse_resource_attributes_explicit_overrides_auto_detected():
    """OTEL_RESOURCE_ATTRIBUTES must take precedence over downward API vars."""
    env = {
        "POD_NAME": "auto-detected-pod",
        "OTEL_RESOURCE_ATTRIBUTES": "k8s.pod.name=explicit-override",
    }
    with patch.dict(os.environ, env, clear=False):
        result = _parse_resource_attributes()
    assert result.get("k8s.pod.name") == "explicit-override"


def test_parse_resource_attributes_merges_both_sources():
    env = {
        "POD_NAME": "le-coffre-backend-abc123",
        "OTEL_RESOURCE_ATTRIBUTES": "app.version=1.2.0",
    }
    with patch.dict(os.environ, env, clear=False):
        result = _parse_resource_attributes()
    assert result.get("k8s.pod.name") == "le-coffre-backend-abc123"
    assert result.get("app.version") == "1.2.0"


# --- Distributed tracing: _try_import_otel ---


def test_try_import_otel_returns_false_when_otel_unavailable(app):
    """_try_import_otel() must return False when _OTEL_AVAILABLE is False."""
    from monitoring import _try_import_otel

    with patch("monitoring._OTEL_AVAILABLE", False):
        result = _try_import_otel()
    assert result is False


def test_setup_monitoring_returns_none_when_disabled(app):
    """setup_monitoring must return None on all no-op paths."""
    # Hard disable
    with patch.dict(os.environ, {"ENABLE_MONITORING": "false"}):
        result = setup_monitoring(app)
    assert result is None

    # No endpoint, no ENABLE_MONITORING=true
    env = {k: v for k, v in os.environ.items() if k not in ("OTEL_EXPORTER_OTLP_ENDPOINT", "ENABLE_MONITORING")}
    with patch.dict(os.environ, env, clear=True):
        result = setup_monitoring(app)
    assert result is None

    # Deps missing
    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch("monitoring._try_import_otel", return_value=False):
            result = setup_monitoring(app)
    assert result is None


def test_setup_monitoring_returns_providers_tuple_when_active(app):
    """setup_monitoring must return a (tracer_provider, meter_provider) tuple when active."""
    fake_tracer = MagicMock(name="tracer_provider")
    fake_meter = MagicMock(name="meter_provider")

    with patch("monitoring._configure_otel", return_value=(fake_tracer, fake_meter)) as mock_cfg:
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            with patch("monitoring._try_import_otel", return_value=True):
                result = setup_monitoring(app)

    mock_cfg.assert_called_once()
    assert result == (fake_tracer, fake_meter)


# --- _build_sampler tests ---


def test_build_sampler_default_returns_parentbased_traceidratio():
    from monitoring import _build_sampler

    mock_parent_based = MagicMock(name="ParentBased")
    mock_traceid_ratio = MagicMock(name="TraceIdRatioBased")

    env = {k: v for k, v in os.environ.items() if k not in ("OTEL_TRACES_SAMPLER", "OTEL_TRACES_SAMPLER_ARG")}
    with patch("monitoring.ParentBased", mock_parent_based):
        with patch("monitoring.TraceIdRatioBased", mock_traceid_ratio):
            with patch.dict(os.environ, env, clear=True):
                _build_sampler()

    mock_traceid_ratio.assert_called_once_with(0.05)
    mock_parent_based.assert_called_once_with(mock_traceid_ratio())


def test_build_sampler_traceidratio():
    from monitoring import _build_sampler

    mock_always_on = MagicMock(name="ALWAYS_ON")
    mock_parent_based = MagicMock(name="ParentBased")
    mock_traceid_ratio = MagicMock(name="TraceIdRatioBased")

    with patch("monitoring.ALWAYS_ON", mock_always_on):
        with patch("monitoring.ParentBased", mock_parent_based):
            with patch("monitoring.TraceIdRatioBased", mock_traceid_ratio):
                with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "traceidratio", "OTEL_TRACES_SAMPLER_ARG": "0.5"}):
                    _build_sampler()

    mock_traceid_ratio.assert_called_once_with(0.5)


def test_build_sampler_invalid_arg_falls_back_to_parentbased(caplog):
    from monitoring import _build_sampler

    mock_always_on = MagicMock(name="ALWAYS_ON")
    mock_parent_based = MagicMock(name="ParentBased")
    mock_traceid_ratio = MagicMock(name="TraceIdRatioBased")

    with patch("monitoring.ALWAYS_ON", mock_always_on):
        with patch("monitoring.ParentBased", mock_parent_based):
            with patch("monitoring.TraceIdRatioBased", mock_traceid_ratio):
                with patch.dict(
                    os.environ, {"OTEL_TRACES_SAMPLER": "traceidratio", "OTEL_TRACES_SAMPLER_ARG": "not-a-float"}
                ):
                    with caplog.at_level(logging.WARNING, logger="monitoring"):
                        _build_sampler()

    mock_parent_based.assert_called_once_with(mock_always_on)
    assert "OTEL_TRACES_SAMPLER_ARG" in caplog.text


def test_build_sampler_out_of_range_falls_back_to_parentbased(caplog):
    from monitoring import _build_sampler

    mock_always_on = MagicMock(name="ALWAYS_ON")
    mock_parent_based = MagicMock(name="ParentBased")
    mock_traceid_ratio = MagicMock(name="TraceIdRatioBased")

    with patch("monitoring.ALWAYS_ON", mock_always_on):
        with patch("monitoring.ParentBased", mock_parent_based):
            with patch("monitoring.TraceIdRatioBased", mock_traceid_ratio):
                with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "traceidratio", "OTEL_TRACES_SAMPLER_ARG": "1.5"}):
                    with caplog.at_level(logging.WARNING, logger="monitoring"):
                        _build_sampler()

    mock_parent_based.assert_called_once_with(mock_always_on)
    assert "OTEL_TRACES_SAMPLER_ARG" in caplog.text


# --- _configure_otel test ---


def test_configure_otel_instruments_sqlalchemy(app):
    """_configure_otel must call SQLAlchemyInstrumentor().instrument()."""
    from monitoring import _configure_otel

    mock_sqla = MagicMock()
    with patch("monitoring._warn_insecure_otlp"):
        with patch("monitoring.SQLAlchemyInstrumentor", mock_sqla):
            with patch("monitoring.HTTPXClientInstrumentor", MagicMock()):
                with patch("monitoring.TracerProvider", MagicMock()):
                    with patch("monitoring.MeterProvider", MagicMock()):
                        with patch("monitoring.OTLPMetricExporter", MagicMock()):
                            with patch("monitoring.OTLPSpanExporter", MagicMock()):
                                with patch("monitoring.PeriodicExportingMetricReader", MagicMock()):
                                    with patch("monitoring.Resource", MagicMock()):
                                        with patch("monitoring.BatchSpanProcessor", MagicMock()):
                                            with patch("monitoring.FastAPIInstrumentor", MagicMock()):
                                                with patch("monitoring.otel_trace", MagicMock()):
                                                    with patch("monitoring.otel_metrics", MagicMock()):
                                                        with patch.dict(
                                                            os.environ,
                                                            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"},
                                                        ):
                                                            _configure_otel(app)
    mock_sqla.return_value.instrument.assert_called_once()


def test_configure_otel_instruments_httpx(app):
    """_configure_otel must call HTTPXClientInstrumentor().instrument()."""
    from monitoring import _configure_otel

    mock_httpx = MagicMock()
    with patch("monitoring._warn_insecure_otlp"):
        with patch("monitoring.SQLAlchemyInstrumentor", MagicMock()):
            with patch("monitoring.HTTPXClientInstrumentor", mock_httpx):
                with patch("monitoring.TracerProvider", MagicMock()):
                    with patch("monitoring.MeterProvider", MagicMock()):
                        with patch("monitoring.OTLPMetricExporter", MagicMock()):
                            with patch("monitoring.OTLPSpanExporter", MagicMock()):
                                with patch("monitoring.PeriodicExportingMetricReader", MagicMock()):
                                    with patch("monitoring.Resource", MagicMock()):
                                        with patch("monitoring.BatchSpanProcessor", MagicMock()):
                                            with patch("monitoring.FastAPIInstrumentor", MagicMock()):
                                                with patch("monitoring.otel_trace", MagicMock()):
                                                    with patch("monitoring.otel_metrics", MagicMock()):
                                                        with patch.dict(
                                                            os.environ,
                                                            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"},
                                                        ):
                                                            _configure_otel(app)
    mock_httpx.return_value.instrument.assert_called_once()


def test_configure_otel_sets_global_tracer_provider(app):
    """_configure_otel must call otel_trace.set_tracer_provider with the created TracerProvider."""
    from monitoring import _configure_otel

    mock_tracer_provider_instance = MagicMock(name="TracerProvider_instance")
    mock_meter_provider_instance = MagicMock(name="MeterProvider_instance")

    mock_tracer_provider_cls = MagicMock(return_value=mock_tracer_provider_instance)
    mock_meter_provider_cls = MagicMock(return_value=mock_meter_provider_instance)
    mock_instrumentor = MagicMock()
    mock_otlp_metric = MagicMock()
    mock_otlp_trace = MagicMock()
    mock_reader = MagicMock()
    mock_resource_cls = MagicMock()
    mock_resource_cls.create.return_value = MagicMock()
    mock_batch_processor = MagicMock()
    mock_otel_trace = MagicMock()
    mock_otel_metrics = MagicMock()
    mock_always_on = MagicMock(name="ALWAYS_ON")
    mock_parent_based = MagicMock(name="ParentBased", side_effect=lambda root: root)
    mock_traceid_ratio = MagicMock(name="TraceIdRatioBased")

    with patch("monitoring._warn_insecure_otlp"):
        with patch("monitoring.otel_trace", mock_otel_trace):
            with patch("monitoring.otel_metrics", mock_otel_metrics):
                with patch("monitoring.TracerProvider", mock_tracer_provider_cls):
                    with patch("monitoring.MeterProvider", mock_meter_provider_cls):
                        with patch("monitoring.OTLPMetricExporter", mock_otlp_metric):
                            with patch("monitoring.OTLPSpanExporter", mock_otlp_trace):
                                with patch("monitoring.PeriodicExportingMetricReader", mock_reader):
                                    with patch("monitoring.Resource", mock_resource_cls):
                                        with patch("monitoring.SERVICE_NAME", "service.name"):
                                            with patch("monitoring.BatchSpanProcessor", mock_batch_processor):
                                                with patch("monitoring.FastAPIInstrumentor", mock_instrumentor):
                                                    with patch("monitoring.ALWAYS_ON", mock_always_on):
                                                        with patch("monitoring.ParentBased", mock_parent_based):
                                                            with patch(
                                                                "monitoring.TraceIdRatioBased", mock_traceid_ratio
                                                            ):
                                                                with patch.dict(
                                                                    os.environ,
                                                                    {
                                                                        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"
                                                                    },
                                                                ):
                                                                    result = _configure_otel(app)

    mock_otel_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
    mock_otel_metrics.set_meter_provider.assert_called_once_with(mock_meter_provider_instance)
    assert result is not None
    tracer_prov, meter_prov = result
    assert tracer_prov is mock_tracer_provider_instance
    assert meter_prov is mock_meter_provider_instance


# --- Task 2: Log/trace correlation in JsonFormatter ---


def test_json_formatter_injects_trace_id_when_span_is_active():
    """When an OTEL span is active, trace_id and span_id must appear in JSON output."""
    mock_ctx = MagicMock()
    mock_ctx.is_valid = True
    mock_ctx.trace_id = 0xABCDEF1234567890ABCDEF1234567890
    mock_ctx.span_id = 0x1234567890ABCDEF

    mock_span = MagicMock()
    mock_span.get_span_context.return_value = mock_ctx

    fmt = JsonFormatter()
    record = _make_application_record()

    with patch.object(otel_trace, "get_current_span", return_value=mock_span):
        parsed = json.loads(fmt.format(record))

    assert "trace_id" in parsed
    assert "span_id" in parsed
    assert len(parsed["trace_id"]) == 32
    assert len(parsed["span_id"]) == 16


def test_json_formatter_no_trace_id_when_no_active_span():
    """When no OTEL span is active (is_valid=False), trace_id must not appear."""
    fmt = JsonFormatter()
    record = _make_application_record()

    # NonRecordingSpan with INVALID_SPAN_CONTEXT is what get_current_span() returns
    # when no span is in context (is_valid=False)
    invalid_span = NonRecordingSpan(INVALID_SPAN_CONTEXT)
    with patch.object(otel_trace, "get_current_span", return_value=invalid_span):
        parsed = json.loads(fmt.format(record))

    assert "trace_id" not in parsed
    assert "span_id" not in parsed


def test_json_formatter_no_trace_id_when_opentelemetry_not_importable():
    """When opentelemetry is not installed, JSON output must not contain trace_id."""
    fmt = JsonFormatter()
    record = _make_application_record()

    with patch("monitoring._OTEL_AVAILABLE", False):
        parsed = json.loads(fmt.format(record))

    assert "trace_id" not in parsed
    assert "span_id" not in parsed


def test_setup_monitoring_returns_providers_that_can_be_shut_down(app):
    """The returned providers must expose and accept force_flush and shutdown calls."""
    with patch("monitoring._configure_otel") as mock_configure:
        mock_tracer = MagicMock()
        mock_meter = MagicMock()
        mock_configure.return_value = (mock_tracer, mock_meter)
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
            with patch("monitoring._try_import_otel", return_value=True):
                result = setup_monitoring(app)

    tracer_p, meter_p = result
    # Call the shutdown methods — the lifespan uses them; they must not raise
    tracer_p.force_flush()
    tracer_p.shutdown()
    meter_p.force_flush()
    meter_p.shutdown()
    tracer_p.force_flush.assert_called_once()
    tracer_p.shutdown.assert_called_once()
    meter_p.force_flush.assert_called_once()
    meter_p.shutdown.assert_called_once()

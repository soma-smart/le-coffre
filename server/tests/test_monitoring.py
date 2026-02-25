import json
import logging
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi import FastAPI

from monitoring import JsonFormatter, setup_monitoring, _UvicornAccessFilter, setup_logging, _parse_resource_attributes


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


# --- _parse_resource_attributes: Kubernetes downward API auto-detection ---


def test_parse_resource_attributes_empty_when_no_env_vars():
    env = {k: v for k, v in os.environ.items()
           if k not in ("OTEL_RESOURCE_ATTRIBUTES", "POD_NAME", "NODE_NAME", "POD_NAMESPACE")}
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


# --- New tests for distributed tracing (Task 1) ---

_TRACE_MODULES = [
    "opentelemetry.sdk.trace",
    "opentelemetry.sdk.trace.export",
    "opentelemetry.exporter.otlp.proto.http.trace_exporter",
]


def test_try_import_otel_returns_false_when_trace_modules_missing(app):
    """_try_import_otel() must return False when trace-specific modules are absent."""
    from monitoring import _try_import_otel

    blocked = {**{mod: None for mod in _OTEL_MODULES}, **{mod: None for mod in _TRACE_MODULES}}
    with patch.dict(sys.modules, blocked):
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


def _make_sampling_modules():
    """Build a sys.modules patch that provides a minimal opentelemetry.sdk.trace.sampling mock."""
    always_on = MagicMock(name="ALWAYS_ON")
    parent_based_cls = MagicMock(name="ParentBased", side_effect=lambda root: MagicMock(spec=["__class__"], _root=root, _ParentBased=True))
    traceid_ratio_cls = MagicMock(name="TraceIdRatioBased", side_effect=lambda ratio: MagicMock(spec=["__class__"], _ratio=ratio, _TraceIdRatio=True))

    sampling_mod = MagicMock(
        ALWAYS_ON=always_on,
        ParentBased=parent_based_cls,
        TraceIdRatioBased=traceid_ratio_cls,
    )
    sdk_trace_mod = MagicMock(sampling=sampling_mod)
    return {
        "opentelemetry": MagicMock(),
        "opentelemetry.sdk": MagicMock(),
        "opentelemetry.sdk.trace": sdk_trace_mod,
        "opentelemetry.sdk.trace.sampling": sampling_mod,
    }, sampling_mod


def test_build_sampler_default_returns_parentbased_always_on():
    from monitoring import _build_sampler
    modules, sampling = _make_sampling_modules()
    env = {k: v for k, v in os.environ.items() if k not in ("OTEL_TRACES_SAMPLER", "OTEL_TRACES_SAMPLER_ARG")}
    with patch.dict(sys.modules, modules):
        with patch.dict(os.environ, env, clear=True):
            sampler = _build_sampler()
    sampling.ParentBased.assert_called_once_with(sampling.ALWAYS_ON)


def test_build_sampler_traceidratio():
    from monitoring import _build_sampler
    modules, sampling = _make_sampling_modules()
    with patch.dict(sys.modules, modules):
        with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "traceidratio", "OTEL_TRACES_SAMPLER_ARG": "0.5"}):
            sampler = _build_sampler()
    sampling.TraceIdRatioBased.assert_called_once_with(0.5)


def test_build_sampler_invalid_arg_falls_back_to_parentbased(caplog):
    from monitoring import _build_sampler
    modules, sampling = _make_sampling_modules()
    with patch.dict(sys.modules, modules):
        with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "traceidratio", "OTEL_TRACES_SAMPLER_ARG": "not-a-float"}):
            with caplog.at_level(logging.WARNING, logger="monitoring"):
                sampler = _build_sampler()
    sampling.ParentBased.assert_called_once_with(sampling.ALWAYS_ON)
    assert "OTEL_TRACES_SAMPLER_ARG" in caplog.text


def test_build_sampler_out_of_range_falls_back_to_parentbased(caplog):
    from monitoring import _build_sampler
    modules, sampling = _make_sampling_modules()
    with patch.dict(sys.modules, modules):
        with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "traceidratio", "OTEL_TRACES_SAMPLER_ARG": "1.5"}):
            with caplog.at_level(logging.WARNING, logger="monitoring"):
                sampler = _build_sampler()
    sampling.ParentBased.assert_called_once_with(sampling.ALWAYS_ON)
    assert "OTEL_TRACES_SAMPLER_ARG" in caplog.text


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

    # `import opentelemetry.trace as otel_trace` resolves by loading `opentelemetry`
    # then reading its `.trace` attribute. We must wire those attributes explicitly
    # so the mock namespace matches what the production code will receive.
    otel_pkg = MagicMock()
    otel_pkg.trace = mock_otel_trace
    otel_pkg.metrics = mock_otel_metrics

    otel_sdk_pkg = MagicMock()
    otel_sdk_trace_module = MagicMock(TracerProvider=mock_tracer_provider_cls)
    otel_sdk_trace_module.sampling = MagicMock(
        ALWAYS_ON=MagicMock(),
        ParentBased=MagicMock(side_effect=lambda root: root),
        TraceIdRatioBased=MagicMock(),
    )
    otel_sdk_pkg.trace = otel_sdk_trace_module

    otel_exporter_pkg = MagicMock()
    otel_instrumentation_pkg = MagicMock()

    modules = {
        "opentelemetry": otel_pkg,
        "opentelemetry.trace": mock_otel_trace,
        "opentelemetry.metrics": mock_otel_metrics,
        "opentelemetry.sdk": otel_sdk_pkg,
        "opentelemetry.sdk.metrics": MagicMock(MeterProvider=mock_meter_provider_cls),
        "opentelemetry.sdk.metrics.export": MagicMock(PeriodicExportingMetricReader=mock_reader),
        "opentelemetry.sdk.resources": MagicMock(Resource=mock_resource_cls, SERVICE_NAME="service.name"),
        "opentelemetry.sdk.trace": otel_sdk_trace_module,
        "opentelemetry.sdk.trace.export": MagicMock(BatchSpanProcessor=mock_batch_processor),
        "opentelemetry.sdk.trace.sampling": otel_sdk_trace_module.sampling,
        "opentelemetry.exporter": otel_exporter_pkg,
        "opentelemetry.exporter.otlp": MagicMock(),
        "opentelemetry.exporter.otlp.proto": MagicMock(),
        "opentelemetry.exporter.otlp.proto.http": MagicMock(),
        "opentelemetry.exporter.otlp.proto.http.metric_exporter": MagicMock(OTLPMetricExporter=mock_otlp_metric),
        "opentelemetry.exporter.otlp.proto.http.trace_exporter": MagicMock(OTLPSpanExporter=mock_otlp_trace),
        "opentelemetry.instrumentation": otel_instrumentation_pkg,
        "opentelemetry.instrumentation.fastapi": MagicMock(FastAPIInstrumentor=mock_instrumentor),
    }

    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318"}):
        with patch.dict(sys.modules, modules):
            result = _configure_otel(app)

    mock_otel_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
    mock_otel_metrics.set_meter_provider.assert_called_once_with(mock_meter_provider_instance)
    assert result is not None
    tracer_prov, meter_prov = result
    assert tracer_prov is mock_tracer_provider_instance
    assert meter_prov is mock_meter_provider_instance

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
                         .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging() -> None:
    """Configure JSON log formatting when LOG_FORMAT=json.

    Opt-in, environment-agnostic. Works in any deployment context.
    Default (no variable set) keeps uvicorn's standard text format.
    Called at module level in main.py — uvicorn configures its loggers before
    importing the app module, so all handlers are already present at call time.
    """
    if os.getenv("LOG_FORMAT", "").lower() != "json":
        return

    formatter = JsonFormatter()
    # Target uvicorn's loggers specifically. If the ASGI server changes,
    # update this list to match the new server's logger hierarchy.
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error"):
        for handler in logging.getLogger(name).handlers:
            handler.setFormatter(formatter)


class _UvicornAccessFilter(logging.Filter):
    """Suppress noisy OK responses from health checks and, when active, the /metrics route."""

    _ALWAYS_SUPPRESSED = frozenset({"/api/health"})
    _MONITORING_SUPPRESSED = frozenset({"/api/metrics"})

    def __init__(self, monitoring_active: bool = True) -> None:
        super().__init__()
        self._suppressed = self._ALWAYS_SUPPRESSED | (
            self._MONITORING_SUPPRESSED if monitoring_active else frozenset()
        )

    def filter(self, record: logging.LogRecord) -> bool:
        # Parse record.args directly — uvicorn access log format is a 5-tuple:
        # (client_addr, method, path, http_version, status_code)
        args = record.args
        if (
            isinstance(args, tuple)
            and len(args) == 5
            and args[1] == "GET"
            and args[2] in self._suppressed
            and args[4] == 200
        ):
            return False
        return True


def setup_monitoring(app) -> tuple | None:
    """Instrument the FastAPI app with OpenTelemetry metrics and traces via OTLP.

    Activation:
    - ENABLE_MONITORING=false → disabled (hard override)
    - OTEL_EXPORTER_OTLP_ENDPOINT not set and ENABLE_MONITORING != true → silent no-op
    - OTel packages not installed → logs INFO and no-op
    - Otherwise → instruments app and exports metrics + traces via OTLP HTTP

    Returns (tracer_provider, meter_provider) when active, None otherwise.
    Callers can use the returned providers for graceful shutdown.
    """
    if os.getenv("ENABLE_MONITORING", "").lower() == "false":
        _install_filter(monitoring_active=False)
        return None

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not endpoint and os.getenv("ENABLE_MONITORING", "").lower() != "true":
        _install_filter(monitoring_active=False)
        return None

    if not endpoint:
        logger.warning(
            "ENABLE_MONITORING=true but OTEL_EXPORTER_OTLP_ENDPOINT is not set — metrics will not be exported"
        )
        _install_filter(monitoring_active=False)
        return None

    if not _try_import_otel():
        _install_filter(monitoring_active=False)
        return None

    providers = _configure_otel(app)
    # OTLP pushes to collector — no /metrics endpoint is mounted.
    _install_filter(monitoring_active=False)
    return providers


def _try_import_otel() -> bool:
    """Attempt to import OTel packages. Returns False and logs if unavailable."""
    try:
        import opentelemetry.instrumentation.fastapi  # noqa: F401
        import opentelemetry.exporter.otlp.proto.http.metric_exporter  # noqa: F401
        import opentelemetry.sdk.metrics  # noqa: F401
        import opentelemetry.sdk.metrics.export  # noqa: F401
        import opentelemetry.sdk.resources  # noqa: F401
        import opentelemetry.sdk.trace  # noqa: F401
        import opentelemetry.sdk.trace.export  # noqa: F401
        import opentelemetry.exporter.otlp.proto.http.trace_exporter  # noqa: F401
        return True
    except ImportError:
        logger.info("Monitoring dependencies not installed, skipping instrumentation")
        return False


def _configure_otel(app) -> tuple:
    """Configure OpenTelemetry metrics and distributed tracing.

    Returns (tracer_provider, meter_provider) for use by the caller
    (e.g. graceful shutdown hooks).
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    import opentelemetry.trace as otel_trace
    import opentelemetry.metrics as otel_metrics

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    service_name = os.getenv("OTEL_SERVICE_NAME", "le-coffre")

    resource = Resource.create({
        SERVICE_NAME: service_name,
        **_parse_resource_attributes(),
    })

    # --- Metrics ---
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    otel_metrics.set_meter_provider(meter_provider)

    # --- Traces ---
    tracer_provider = TracerProvider(resource=resource, sampler=_build_sampler())
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        )
    )
    otel_trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/api/health,/api/metrics",
        meter_provider=meter_provider,
        tracer_provider=tracer_provider,
    )

    logger.info(
        "OpenTelemetry enabled — service=%s endpoint=%s",
        service_name,
        endpoint,
    )

    return tracer_provider, meter_provider


def _build_sampler():
    """Build a trace sampler from OTEL_TRACES_SAMPLER / OTEL_TRACES_SAMPLER_ARG env vars."""
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased, TraceIdRatioBased

    name = os.getenv("OTEL_TRACES_SAMPLER", "parentbased_always_on")
    raw_arg = os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0")

    try:
        ratio = float(raw_arg)
    except ValueError:
        logger.warning(
            "Invalid OTEL_TRACES_SAMPLER_ARG=%r — must be a float in [0.0, 1.0], falling back to ParentBased(ALWAYS_ON)",
            raw_arg,
        )
        return ParentBased(ALWAYS_ON)

    if name in ("traceidratio", "parentbased_traceidratio") and not (0.0 <= ratio <= 1.0):
        logger.warning(
            "OTEL_TRACES_SAMPLER_ARG=%r is outside [0.0, 1.0] — falling back to ParentBased(ALWAYS_ON)",
            raw_arg,
        )
        return ParentBased(ALWAYS_ON)

    if name == "traceidratio":
        return TraceIdRatioBased(ratio)
    if name == "parentbased_traceidratio":
        return ParentBased(TraceIdRatioBased(ratio))
    return ParentBased(ALWAYS_ON)


def _parse_resource_attributes() -> dict:
    """Build OTEL resource attributes from env vars.

    Merges two sources (explicit wins over auto-detected):
    1. Well-known Kubernetes downward API env vars (POD_NAME, NODE_NAME,
       POD_NAMESPACE) are mapped to OTel semantic convention attribute names.
    2. OTEL_RESOURCE_ATTRIBUTES (key=value,key2=value2) overrides any
       auto-detected value for the same key.
    """
    _K8S_ENV_MAPPING = {
        "POD_NAME": "k8s.pod.name",
        "NODE_NAME": "k8s.node.name",
        "POD_NAMESPACE": "k8s.namespace.name",
    }
    result = {
        otel_key: value
        for env_var, otel_key in _K8S_ENV_MAPPING.items()
        if (value := os.getenv(env_var))
    }

    raw = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
    for pair in raw.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()

    return result


def _install_filter(monitoring_active: bool) -> None:
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.filters = [
        f for f in uvicorn_logger.filters if not isinstance(f, _UvicornAccessFilter)
    ]
    uvicorn_logger.addFilter(_UvicornAccessFilter(monitoring_active=monitoring_active))

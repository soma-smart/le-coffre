import json
import logging
import os
from datetime import datetime, timezone

# Optional OpenTelemetry SDK — installed via the [monitoring] dependency group.
try:
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    import opentelemetry.metrics as otel_metrics
    import opentelemetry.trace as otel_trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased, TraceIdRatioBased
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)

# Standard LogRecord attributes — excluded from the extra-fields merge.
_LOGRECORD_RESERVED = frozenset({
    "name", "msg", "args", "created", "filename", "funcName", "levelname",
    "levelno", "lineno", "module", "msecs", "pathname", "process",
    "processName", "relativeCreated", "stack_info", "thread", "threadName",
    "exc_info", "exc_text", "message", "taskName",
})


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
        # Merge extra fields passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in _LOGRECORD_RESERVED and not key.startswith("_") and key not in entry:
                try:
                    json.dumps(value)
                    entry[key] = value
                except (TypeError, ValueError):
                    entry[key] = str(value)
        # Inject OTEL trace context for log/trace correlation when a span is active
        if _OTEL_AVAILABLE:
            span = otel_trace.get_current_span()
            ctx = span.get_span_context()
            if ctx.is_valid:
                entry["trace_id"] = format(ctx.trace_id, "032x")
                entry["span_id"] = format(ctx.span_id, "016x")
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
    """Check if OTel packages are available. Returns False and logs if not."""
    if not _OTEL_AVAILABLE:
        logger.info("Monitoring dependencies not installed, skipping instrumentation")
    return _OTEL_AVAILABLE


# Routes excluded from span instrumentation — all routes that handle secret material
# (vault shares, credentials, plaintext passwords) must be listed here so that
# the OTel HTTP instrumentation never creates spans for them, preventing any
# accidental capture of sensitive data in span attributes or exception events.
_EXCLUDED_URLS = ",".join([
    "/api/health",
    "/api/metrics",
    "/api/vault/unlock",
    "/api/vault/setup",
    "/api/vault/validate-setup",
    "/api/auth/login",
    "/api/auth/register-admin",
    "/api/auth/refresh-token",
    "/api/users/me/password",
    "/api/passwords",
])


def _configure_otel(app) -> tuple:
    """Configure OpenTelemetry metrics and distributed tracing.

    Returns (tracer_provider, meter_provider) for use by the caller
    (e.g. graceful shutdown hooks).
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    service_name = os.getenv("OTEL_SERVICE_NAME", "le-coffre")

    _warn_insecure_otlp(endpoint)

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
        # Exclude all routes that handle secret material — see _EXCLUDED_URLS above.
        excluded_urls=_EXCLUDED_URLS,
        meter_provider=meter_provider,
        tracer_provider=tracer_provider,
    )
    SQLAlchemyInstrumentor().instrument(
        tracer_provider=tracer_provider,
        enable_commenter=True,
        # Never capture bound parameter values — queries may reference encrypted
        # content or user identifiers that should not appear in trace backends.
        capture_parameters=False,
    )
    HTTPXClientInstrumentor().instrument(
        tracer_provider=tracer_provider,
    )

    logger.info(
        "OpenTelemetry enabled — service=%s endpoint=%s",
        service_name,
        endpoint,
    )

    return tracer_provider, meter_provider


def _warn_insecure_otlp(endpoint: str) -> None:
    """Emit warnings when the OTLP transport is insecure or unauthenticated."""
    if endpoint.startswith("http://"):
        logger.warning(
            "OTLP endpoint uses plain HTTP — telemetry may be intercepted in transit. "
            "Set OTEL_EXPORTER_OTLP_ENDPOINT to an https:// URL for production deployments."
        )
    if not os.getenv("OTEL_EXPORTER_OTLP_HEADERS"):
        logger.warning(
            "OTEL_EXPORTER_OTLP_HEADERS is not set — telemetry is exported without authentication. "
            "Configure a bearer token via OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <token>."
        )


def _build_sampler():
    """Build a trace sampler from OTEL_TRACES_SAMPLER / OTEL_TRACES_SAMPLER_ARG env vars.

    Defaults to 5% sampling (parentbased_traceidratio at 0.05) to limit the
    volume of telemetry exported and reduce exposure of request metadata.
    Set OTEL_TRACES_SAMPLER=parentbased_always_on to capture 100% of traces.
    """
    name = os.getenv("OTEL_TRACES_SAMPLER", "parentbased_traceidratio")
    raw_arg = os.getenv("OTEL_TRACES_SAMPLER_ARG", "0.05")

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
            k = k.strip()
            v = v.strip()
            # Protect service.name — it is already set from OTEL_SERVICE_NAME above
            # and must not be overridden by a generic resource attribute.
            if k and k != SERVICE_NAME:
                result[k] = v

    return result


def _install_filter(monitoring_active: bool) -> None:
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.filters = [
        f for f in uvicorn_logger.filters if not isinstance(f, _UvicornAccessFilter)
    ]
    uvicorn_logger.addFilter(_UvicornAccessFilter(monitoring_active=monitoring_active))

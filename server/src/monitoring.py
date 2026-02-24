import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for Loki ingestion."""

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


def setup_monitoring(app) -> None:
    """Instrument the FastAPI app with OpenTelemetry metrics via OTLP.

    Activation:
    - ENABLE_MONITORING=false → disabled (hard override)
    - OTEL_EXPORTER_OTLP_ENDPOINT not set and ENABLE_MONITORING != true → silent no-op
    - OTel packages not installed → logs INFO and no-op
    - Otherwise → instruments app and exports metrics via OTLP HTTP
    """
    if os.getenv("ENABLE_MONITORING", "").lower() == "false":
        _install_filter(monitoring_active=False)
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not endpoint and os.getenv("ENABLE_MONITORING", "").lower() != "true":
        _install_filter(monitoring_active=False)
        return

    if not endpoint:
        logger.warning(
            "ENABLE_MONITORING=true but OTEL_EXPORTER_OTLP_ENDPOINT is not set — metrics will not be exported"
        )
        _install_filter(monitoring_active=False)
        return

    if not _try_import_otel():
        _install_filter(monitoring_active=False)
        return

    _configure_otel(app)
    # OTLP pushes to collector — no /metrics endpoint is mounted.
    _install_filter(monitoring_active=False)


def _try_import_otel() -> bool:
    """Attempt to import OTel packages. Returns False and logs if unavailable."""
    try:
        import opentelemetry.instrumentation.fastapi  # noqa: F401
        import opentelemetry.exporter.otlp.proto.http.metric_exporter  # noqa: F401
        import opentelemetry.sdk.metrics  # noqa: F401
        import opentelemetry.sdk.metrics.export  # noqa: F401
        import opentelemetry.sdk.resources  # noqa: F401
        return True
    except ImportError:
        logger.info("Monitoring dependencies not installed, skipping instrumentation")
        return False


def _configure_otel(app) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    service_name = os.getenv("OTEL_SERVICE_NAME", "le-coffre")

    resource = Resource.create({
        SERVICE_NAME: service_name,
        **_parse_resource_attributes(),
    })

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/api/health,/api/metrics",
        meter_provider=provider,
    )

    logger.info(
        "OpenTelemetry metrics enabled — service=%s endpoint=%s",
        service_name,
        endpoint,
    )


def _parse_resource_attributes() -> dict:
    """Parse OTEL_RESOURCE_ATTRIBUTES env var into a dict.

    Format: key=value,key2=value2
    """
    raw = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
    if not raw:
        return {}
    result = {}
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

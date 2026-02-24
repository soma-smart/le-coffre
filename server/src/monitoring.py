import logging
import os

logger = logging.getLogger(__name__)


class _UvicornAccessFilter(logging.Filter):
    """Suppress noisy OK responses from health checks and, when active, Prometheus scrapes."""

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
    """Instrument the FastAPI app with OpenTelemetry metrics.

    Does nothing if ENABLE_MONITORING=false or if OTel packages are not installed.
    """
    if os.getenv("ENABLE_MONITORING", "").lower() == "false":
        _install_filter(monitoring_active=False)
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
        from opentelemetry.sdk.metrics import MeterProvider
    except ImportError:
        logger.info("Monitoring dependencies not installed, skipping instrumentation")
        _install_filter(monitoring_active=False)
        return

    _configure_otel(app, FastAPIInstrumentor, PrometheusMetricReader, MeterProvider)
    _install_filter(monitoring_active=True)


def _install_filter(monitoring_active: bool) -> None:
    uvicorn_logger = logging.getLogger("uvicorn.access")
    # Remove any previously installed instance to avoid duplicates on re-calls.
    uvicorn_logger.filters = [
        f for f in uvicorn_logger.filters if not isinstance(f, _UvicornAccessFilter)
    ]
    uvicorn_logger.addFilter(_UvicornAccessFilter(monitoring_active=monitoring_active))


def _configure_otel(app, FastAPIInstrumentor, PrometheusMetricReader, MeterProvider) -> None:
    import prometheus_client

    reader = PrometheusMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics",
        meter_provider=provider,
    )

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        from fastapi.responses import Response
        data = prometheus_client.generate_latest()
        return Response(content=data, media_type=prometheus_client.CONTENT_TYPE_LATEST)

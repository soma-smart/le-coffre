"""Shared application-level metrics.

Counters are created at import time via the OTel ProxyMeter, which means
they work as no-ops before a MeterProvider is configured and automatically
start recording once setup_monitoring() sets the global provider.

When the opentelemetry package is not installed the counters fall back to
lightweight no-op stubs so callers never need to guard against ImportError.
"""

try:
    import opentelemetry.metrics as otel_metrics

    _meter = otel_metrics.get_meter("le-coffre")
    access_check_not_found_counter = _meter.create_counter(
        "access.check.not_found",
        unit="1",
        description="Number of access checks that returned NOT_FOUND (resource missing or no permission).",
    )
except ImportError:

    class _NoOpCounter:
        def add(self, *_, **__):
            pass

    access_check_not_found_counter = _NoOpCounter()

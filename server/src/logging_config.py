"""JSON structured logging configuration for Loki ingestion.

Replaces all log handlers with a JSON formatter so that Loki can parse and
index logs by field (level, logger, trace_id, ...) using LogQL.

Usage:
  1. Call configure_logging() once at module import time in main.py.
  2. Add _TraceIdMiddleware to the FastAPI app (sets trace_id per request).
  3. Call rewire_uvicorn_logging() at lifespan startup to handle deployment
     scenarios where uvicorn re-initialises its handlers after importing the
     application module (e.g. --reload, gunicorn workers).
"""

import contextvars
import datetime
import json
import logging

# Per-request trace ID — set by _TraceIdMiddleware, read by _TraceIdFilter.
# Will be replaced by the actual OpenTelemetry trace ID in Priority 3 (Tempo).
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        doc: dict = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Preserve extra fields injected via logger.info("...", extra={...}),
        # including trace_id added by _TraceIdFilter.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and not key.startswith("_"):
                doc[key] = value
        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)
        return json.dumps(doc, ensure_ascii=False, default=str)


# Fields that belong to the LogRecord itself — excluded to avoid noise in JSON.
_STANDARD_LOG_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class _TraceIdFilter(logging.Filter):
    """Inject the current request's trace_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace_id_var.get()  # type: ignore[attr-defined]
        return True


_CONFIGURED = False


def configure_logging() -> None:
    """Switch all log handlers to JSON output.

    Idempotent — safe to call multiple times (no-op after the first call).
    Must be called before any logger emits records.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    formatter = _JsonFormatter()
    trace_filter = _TraceIdFilter()

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(formatter)
    root.addFilter(trace_filter)

    # Apply to uvicorn/fastapi loggers in case they already have handlers at
    # this point (normal production case: uvicorn sets up logging before
    # importing the application module).
    rewire_uvicorn_logging()


def rewire_uvicorn_logging() -> None:
    """Re-apply the JSON formatter and trace filter to uvicorn's own handlers.

    Called from both configure_logging() and the lifespan startup to handle
    scenarios where uvicorn re-initialises its handlers after the application
    module is imported (e.g. --reload, gunicorn workers).
    """
    formatter = _JsonFormatter()
    trace_filter = _TraceIdFilter()

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "sqlalchemy.engine"):
        lgr = logging.getLogger(name)
        for handler in lgr.handlers:
            handler.setFormatter(formatter)
        if not any(isinstance(f, _TraceIdFilter) for f in lgr.filters):
            lgr.addFilter(trace_filter)

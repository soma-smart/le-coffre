"""JSON structured logging configuration for Loki ingestion.

Replaces all uvicorn and application log handlers with a JSON formatter so that
Loki can parse and index logs by field (level, logger, trace_id, ...) using LogQL.

Usage: call configure_logging() once at module import time in main.py, before
any logger is used.
"""

import datetime
import json
import logging


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
        # Preserve extra fields injected via logger.info("...", extra={...})
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and not key.startswith("_"):
                doc[key] = value
        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)
        return json.dumps(doc, ensure_ascii=False, default=str)


# Fields that belong to the LogRecord itself — we skip them to avoid noise.
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


def configure_logging() -> None:
    """Switch all log handlers to JSON output.

    Must be called before any logger emits records so that the formatter is in
    place when uvicorn and FastAPI start producing output.
    """
    formatter = _JsonFormatter()

    # Configure the root logger first so any logger that doesn't propagate
    # through a named ancestor still gets the JSON formatter.
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(formatter)

    # Explicitly reconfigure uvicorn loggers (they may have been initialised
    # before our app module was imported by uvicorn).
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "sqlalchemy.engine"):
        lgr = logging.getLogger(name)
        for handler in lgr.handlers:
            handler.setFormatter(formatter)

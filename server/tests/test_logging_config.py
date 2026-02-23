"""Tests for logging_config: _JsonFormatter, _TraceIdFilter, configure_logging."""

import json
import logging
import sys

import pytest

import logging_config
from logging_config import (
    _JsonFormatter,
    _TraceIdFilter,
    _trace_id_var,
    configure_logging,
)


@pytest.fixture(autouse=True)
def reset_configure_flag(monkeypatch):
    """Reset the idempotency guard before each test so configure_logging() runs fresh."""
    monkeypatch.setattr(logging_config, "_CONFIGURED", False)


# ---------------------------------------------------------------------------
# _JsonFormatter
# ---------------------------------------------------------------------------

class TestJsonFormatter:
    def _record(self, msg: str = "hello", level: int = logging.INFO, **extra) -> logging.LogRecord:
        r = logging.LogRecord("test.logger", level, "", 0, msg, (), None)
        for k, v in extra.items():
            setattr(r, k, v)
        return r

    def test_output_is_valid_json(self):
        output = _JsonFormatter().format(self._record())
        assert isinstance(json.loads(output), dict)

    def test_required_fields_present(self):
        parsed = json.loads(_JsonFormatter().format(self._record("hello world")))
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "info"
        assert parsed["logger"] == "test.logger"
        assert "timestamp" in parsed

    def test_extra_fields_included(self):
        parsed = json.loads(_JsonFormatter().format(self._record(request_id="abc-123")))
        assert parsed["request_id"] == "abc-123"

    def test_standard_attrs_not_leaked(self):
        parsed = json.loads(_JsonFormatter().format(self._record()))
        for attr in ("msg", "args", "lineno", "pathname", "funcName", "levelno"):
            assert attr not in parsed

    def test_exception_field_populated(self):
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
        r = self._record()
        r.exc_info = exc_info
        parsed = json.loads(_JsonFormatter().format(r))
        assert "exception" in parsed
        assert "ValueError: boom" in parsed["exception"]

    def test_non_serializable_extra_uses_str_fallback(self):
        r = self._record()
        r.obj = object()  # not JSON-serializable
        output = _JsonFormatter().format(r)  # must not raise
        assert isinstance(json.loads(output), dict)


# ---------------------------------------------------------------------------
# _TraceIdFilter
# ---------------------------------------------------------------------------

class TestTraceIdFilter:
    def test_injects_current_trace_id(self):
        token = _trace_id_var.set("req-abc-123")
        try:
            r = logging.LogRecord("x", logging.INFO, "", 0, "msg", (), None)
            _TraceIdFilter().filter(r)
            assert r.trace_id == "req-abc-123"
        finally:
            _trace_id_var.reset(token)

    def test_default_is_dash_outside_request(self):
        r = logging.LogRecord("x", logging.INFO, "", 0, "msg", (), None)
        _TraceIdFilter().filter(r)
        assert r.trace_id == "-"

    def test_filter_always_returns_true(self):
        r = logging.LogRecord("x", logging.INFO, "", 0, "msg", (), None)
        assert _TraceIdFilter().filter(r) is True


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------

class TestConfigureLogging:
    def test_root_handler_uses_json_formatter(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        try:
            root.handlers.clear()
            configure_logging()
            assert any(isinstance(h.formatter, _JsonFormatter) for h in root.handlers)
        finally:
            root.handlers[:] = original_handlers
            root.setLevel(original_level)

    def test_root_level_set_to_info(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        try:
            root.handlers.clear()
            root.setLevel(logging.WARNING)
            configure_logging()
            assert root.level == logging.INFO
        finally:
            root.handlers[:] = original_handlers
            root.setLevel(original_level)

    def test_idempotent_no_duplicate_handlers(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        try:
            root.handlers.clear()
            configure_logging()
            count_after_first = len(root.handlers)
            # Second call: _CONFIGURED is True — must be a no-op.
            configure_logging()
            assert len(root.handlers) == count_after_first
        finally:
            root.handlers[:] = original_handlers
            root.setLevel(original_level)

    def test_trace_id_filter_added_to_root(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_filters = root.filters[:]
        original_level = root.level
        try:
            root.handlers.clear()
            root.filters.clear()
            configure_logging()
            assert any(isinstance(f, _TraceIdFilter) for f in root.filters)
        finally:
            root.handlers[:] = original_handlers
            root.filters[:] = original_filters
            root.setLevel(original_level)

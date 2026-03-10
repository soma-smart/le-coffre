"""Distributed tracing utilities for use cases and the shared kernel."""

import functools
import inspect

try:
    import opentelemetry.trace as otel_trace
    from opentelemetry.trace import StatusCode

    tracer = otel_trace.get_tracer(__name__)
except ImportError:
    # opentelemetry is not installed — use no-op stubs
    class _NoOpSpan:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def set_attribute(self, *_):
            pass

        def set_status(self, *_):
            pass

        def record_exception(self, *_):
            pass

    class _NoOpTracer:
        def start_as_current_span(self, *_, **__):
            return _NoOpSpan()

    class StatusCode:
        ERROR = "ERROR"
        OK = "OK"

    tracer = _NoOpTracer()

_ALLOWED_ATTRIBUTES = frozenset(
    {
        "app.use_case",
        "app.bounded_context",
        "user.id",
        "db.system",
        "db.operation",
        "http.method",
        "http.route",
        "http.status_code",
        "error.type",
    }
)

_TRACED = "_traced_execute"


def safe_set_attributes(span, attrs: dict) -> None:
    """Set span attributes, filtering to the allowlist only."""
    for key, value in attrs.items():
        if key in _ALLOWED_ATTRIBUTES:
            span.set_attribute(key, str(value))


def _wrap_execute(fn):
    """Wrap a use case execute() method in an OTEL span.

    Handles both synchronous and asynchronous execute() implementations.
    """
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(self, *args, **kwargs):
            span_name = f"{type(self).__name__}.execute"
            with tracer.start_as_current_span(span_name) as span:
                safe_set_attributes(span, {"app.use_case": type(self).__name__})
                try:
                    return await fn(self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(StatusCode.ERROR, str(exc))
                    span.record_exception(exc)
                    raise

        setattr(async_wrapper, _TRACED, True)
        return async_wrapper

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        span_name = f"{type(self).__name__}.execute"
        with tracer.start_as_current_span(span_name) as span:
            safe_set_attributes(span, {"app.use_case": type(self).__name__})
            try:
                return fn(self, *args, **kwargs)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    setattr(wrapper, _TRACED, True)
    return wrapper


class TracedUseCase:
    """
    Mixin that wraps execute() in an OTEL span named 'ClassName.execute'.

    No-op if no TracerProvider is configured.

    Usage:
        class MyUseCase(TracedUseCase):
            def execute(self, command): ...
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "execute" in cls.__dict__ and not getattr(cls.__dict__["execute"], _TRACED, False):
            cls.execute = _wrap_execute(cls.__dict__["execute"])

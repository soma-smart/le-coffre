import asyncio
import pytest
pytest.importorskip("opentelemetry")
from unittest.mock import MagicMock, patch
from opentelemetry.trace import StatusCode
from shared_kernel.application.tracing import TracedUseCase, safe_set_attributes


class ConcreteUseCase(TracedUseCase):
    def execute(self, value: int) -> int:
        return value * 2


class FailingUseCase(TracedUseCase):
    def execute(self):
        raise ValueError("business error")


def test_traced_use_case_returns_result():
    assert ConcreteUseCase().execute(5) == 10


def test_traced_use_case_propagates_exception():
    with pytest.raises(ValueError, match="business error"):
        FailingUseCase().execute()


def test_traced_use_case_creates_span_with_correct_name():
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.application.tracing.tracer", mock_tracer):
        ConcreteUseCase().execute(3)

    mock_tracer.start_as_current_span.assert_called_once_with("ConcreteUseCase.execute")


def test_traced_use_case_sets_use_case_attribute():
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.application.tracing.tracer", mock_tracer):
        ConcreteUseCase().execute(1)

    mock_span.set_attribute.assert_any_call("app.use_case", "ConcreteUseCase")


def test_traced_use_case_marks_span_error_on_exception():
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.application.tracing.tracer", mock_tracer):
        with pytest.raises(ValueError):
            FailingUseCase().execute()

    mock_span.set_status.assert_called_once()
    mock_span.record_exception.assert_called_once()
    # Verify status is ERROR
    call_args = mock_span.set_status.call_args
    assert call_args[0][0] == StatusCode.ERROR


def test_safe_set_attributes_only_sets_allowlisted_keys():
    mock_span = MagicMock()
    safe_set_attributes(mock_span, {
        "user.id": "abc123",
        "user.password": "secret",      # must be blocked
        "db.operation": "commit",
        "unknown.custom": "value",      # must be blocked
        "app.use_case": "MyUseCase",
    })
    set_keys = {call.args[0] for call in mock_span.set_attribute.call_args_list}
    assert "user.id" in set_keys
    assert "db.operation" in set_keys
    assert "app.use_case" in set_keys
    assert "user.password" not in set_keys
    assert "unknown.custom" not in set_keys


def test_safe_set_attributes_converts_values_to_str():
    mock_span = MagicMock()
    safe_set_attributes(mock_span, {"user.id": 12345})
    mock_span.set_attribute.assert_called_once_with("user.id", "12345")


def test_safe_set_attributes_empty_dict_does_nothing():
    mock_span = MagicMock()
    safe_set_attributes(mock_span, {})
    mock_span.set_attribute.assert_not_called()


def test_traced_use_case_no_double_wrap_on_subclass():
    """A subclass defining execute must only wrap the span once."""
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    class ChildUseCase(ConcreteUseCase):
        def execute(self, value: int) -> int:
            return value + 1

    with patch("shared_kernel.application.tracing.tracer", mock_tracer):
        ChildUseCase().execute(1)

    assert mock_tracer.start_as_current_span.call_count == 1


# --- Async use case tests ---

class AsyncUseCase(TracedUseCase):
    async def execute(self, value: int) -> int:
        return value * 3


class AsyncFailingUseCase(TracedUseCase):
    async def execute(self):
        raise ValueError("async error")


def test_traced_use_case_async_returns_result():
    result = asyncio.run(AsyncUseCase().execute(4))
    assert result == 12


def test_traced_use_case_async_propagates_exception():
    with pytest.raises(ValueError, match="async error"):
        asyncio.run(AsyncFailingUseCase().execute())


def test_traced_use_case_async_marks_span_error():
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.application.tracing.tracer", mock_tracer):
        with pytest.raises(ValueError):
            asyncio.run(AsyncFailingUseCase().execute())

    mock_span.set_status.assert_called_once()
    mock_span.record_exception.assert_called_once()
    assert mock_span.set_status.call_args[0][0] == StatusCode.ERROR



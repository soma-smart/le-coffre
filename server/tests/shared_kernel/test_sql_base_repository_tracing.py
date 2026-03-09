import pytest

pytest.importorskip("opentelemetry")
from unittest.mock import MagicMock, patch

from opentelemetry.trace import StatusCode

from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository


@pytest.fixture
def repo():
    session = MagicMock()
    return SQLBaseRepository(session)


def test_commit_creates_db_commit_span(repo):
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.adapters.secondary.sql.sql_base_repository.tracer", mock_tracer):
        repo.commit()

    mock_tracer.start_as_current_span.assert_called_once_with("db.commit")
    mock_span.set_attribute.assert_called_with("db.operation", "commit")


def test_commit_marks_span_error_on_exception(repo):
    repo._session.commit.side_effect = RuntimeError("db down")
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.adapters.secondary.sql.sql_base_repository.tracer", mock_tracer):
        with pytest.raises(RuntimeError):
            repo.commit()

    mock_span.set_status.assert_called_once()
    mock_span.record_exception.assert_called_once()
    status_arg = mock_span.set_status.call_args[0][0]
    assert status_arg == StatusCode.ERROR


def test_commit_and_refresh_creates_span(repo):
    obj = MagicMock()
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.adapters.secondary.sql.sql_base_repository.tracer", mock_tracer):
        repo.commit_and_refresh(obj)

    mock_tracer.start_as_current_span.assert_called_once_with("db.commit_and_refresh")
    mock_span.set_attribute.assert_called_with("db.operation", "commit_and_refresh")


def test_commit_and_refresh_marks_span_error_on_exception(repo):
    repo._session.commit.side_effect = RuntimeError("constraint violation")
    obj = MagicMock()
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("shared_kernel.adapters.secondary.sql.sql_base_repository.tracer", mock_tracer):
        with pytest.raises(RuntimeError):
            repo.commit_and_refresh(obj)

    mock_span.set_status.assert_called_once()
    mock_span.record_exception.assert_called_once()
    status_arg = mock_span.set_status.call_args[0][0]
    assert status_arg == StatusCode.ERROR

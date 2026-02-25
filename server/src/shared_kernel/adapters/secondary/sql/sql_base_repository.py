"""
Base repository class with automatic transaction management.

This class provides automatic rollback on exceptions, preventing developers
from forgetting to add rollback logic in individual repository methods.
"""

from typing import Any
from sqlmodel import Session
import logging

try:
    import opentelemetry.trace as otel_trace
    from opentelemetry.trace import StatusCode
    tracer = otel_trace.get_tracer(__name__)
except ImportError:
    import types

    class _NoOpSpan:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def set_attribute(self, *_): pass
        def set_status(self, *_): pass
        def record_exception(self, *_): pass

    class _NoOpTracer:
        def start_as_current_span(self, *_, **__): return _NoOpSpan()

    class StatusCode:
        ERROR = "ERROR"

    tracer = _NoOpTracer()

logger = logging.getLogger(__name__)


class SQLBaseRepository:
    """
    Base repository class that provides automatic transaction management.

    All write operations (commit) are automatically wrapped with rollback
    on exception handling. Each operation is also instrumented with an
    OTEL span for distributed tracing.

    Usage:
        class SqlUserRepository(SQLBaseRepository, UserRepository):
            def save(self, user: User) -> None:
                db_obj = UserTable(**user.dict())
                self._session.add(db_obj)
                self.commit()  # Automatically handles rollback on error
    """

    def __init__(self, session: Session):
        self._session = session

    def commit(self) -> None:
        """
        Commit the session with automatic rollback on exception.

        This method should be used instead of self._session.commit()
        in all repository methods. The operation is traced with an OTEL span.

        Raises:
            The original exception after rolling back the transaction.
        """
        with tracer.start_as_current_span("db.commit") as span:
            span.set_attribute("db.operation", "commit")  # safe: hardcoded constant
            try:
                self._session.commit()
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                logger.exception("Transaction failed")
                self._session.rollback()
                raise

    def commit_and_refresh(self, obj: Any) -> None:
        """
        Commit the session and refresh an object with automatic rollback on exception.

        The operation is traced with an OTEL span.

        Args:
            obj: The database object to refresh after commit

        Raises:
            The original exception after rolling back the transaction.
        """
        with tracer.start_as_current_span("db.commit_and_refresh") as span:
            span.set_attribute("db.operation", "commit_and_refresh")  # safe: hardcoded constant
            try:
                self._session.commit()
                self._session.refresh(obj)
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                logger.exception("Transaction failed")
                self._session.rollback()
                raise

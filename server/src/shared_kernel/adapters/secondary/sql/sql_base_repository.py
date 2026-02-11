"""
Base repository class with automatic transaction management.

This class provides automatic rollback on exceptions, preventing developers
from forgetting to add rollback logic in individual repository methods.
"""

from typing import Any
from sqlmodel import Session
import logging

logger = logging.getLogger(__name__)


class SQLBaseRepository:
    """
    Base repository class that provides automatic transaction management.

    All write operations (commit) are automatically wrapped with rollback
    on exception handling.

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
        in all repository methods.

        Raises:
            The original exception after rolling back the transaction.
        """
        try:
            self._session.commit()
        except Exception as e:
            logger.exception("Transaction failed")
            self._session.rollback()
            raise

    def commit_and_refresh(self, obj: Any) -> None:
        """
        Commit the session and refresh an object with automatic rollback on exception.

        Args:
            obj: The database object to refresh after commit

        Raises:
            The original exception after rolling back the transaction.
        """
        try:
            self._session.commit()
            self._session.refresh(obj)
        except Exception as e:
            logger.exception("Transaction failed")
            self._session.rollback()
            raise

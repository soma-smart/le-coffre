import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session

from shared_kernel.application.gateways import TransactionGateway, TransactionRolledBackError

logger = logging.getLogger(__name__)

# Kept on the session itself, so every repository sharing it sees the block.
_ATOMIC_DEPTH = "shared_kernel.atomic_depth"
# Set when an inner block fails: the outermost one must not commit then.
_ROLLBACK_ONLY = "shared_kernel.atomic_rollback_only"


def in_atomic_block(session: Session) -> bool:
    return session.info.get(_ATOMIC_DEPTH, 0) > 0


class SqlTransactionGateway(TransactionGateway):
    """Atomic blocks over the request's session.

    Works with the repositories built on the same session: while a block is
    open, SQLBaseRepository.commit() only flushes, and the outermost block
    commits or rolls back everything at once.

    Nested blocks get no SAVEPOINT: with SQLite's default driver, a savepoint
    opened before any write commits on release, outside the enclosing
    transaction. A failed inner block dooms the whole transaction instead.
    """

    def __init__(self, session: Session):
        self._session = session

    @contextmanager
    def atomic(self) -> Iterator[None]:
        info = self._session.info
        depth = info.get(_ATOMIC_DEPTH, 0)
        info[_ATOMIC_DEPTH] = depth + 1
        try:
            yield
        except BaseException:
            if depth == 0:
                info.pop(_ROLLBACK_ONLY, None)
                self._session.rollback()
            else:
                info[_ROLLBACK_ONLY] = True
            raise
        finally:
            info[_ATOMIC_DEPTH] = depth

        if depth > 0:
            return
        if info.pop(_ROLLBACK_ONLY, False):
            self._session.rollback()
            raise TransactionRolledBackError()
        try:
            self._session.commit()
        except Exception:
            logger.exception("Transaction failed")
            self._session.rollback()
            raise

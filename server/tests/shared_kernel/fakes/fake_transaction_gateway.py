from collections.abc import Iterator
from contextlib import contextmanager

from shared_kernel.application.gateways import TransactionGateway, TransactionRolledBackError


class FakeTransactionGateway(TransactionGateway):
    """Records how atomic blocks end.

    Fake repositories have nothing to roll back, so use case tests check what
    happens around the block; the rollback itself is covered against SQL.
    """

    def __init__(self):
        self.committed = 0
        self.rolled_back = 0
        self.commit_error: Exception | None = None
        self._depth = 0
        self._rollback_only = False

    @contextmanager
    def atomic(self) -> Iterator[None]:
        # Same contract as SqlTransactionGateway: only the outermost block
        # ends the transaction, and a failed inner block dooms it.
        outermost = self._depth == 0
        self._depth += 1
        try:
            yield
        except Exception:
            if outermost:
                self._rollback_only = False
                self.rolled_back += 1
            else:
                self._rollback_only = True
            raise
        finally:
            self._depth -= 1
        if not outermost:
            return
        if self._rollback_only:
            self._rollback_only = False
            self.rolled_back += 1
            raise TransactionRolledBackError()
        if self.commit_error is not None:
            self.rolled_back += 1
            raise self.commit_error
        self.committed += 1

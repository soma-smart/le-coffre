from contextlib import AbstractContextManager
from typing import Protocol


class TransactionRolledBackError(RuntimeError):
    """An inner atomic block failed, so the enclosing one rolled everything back
    instead of committing, although the failure was caught in between."""

    def __init__(self) -> None:
        super().__init__("The transaction was rolled back: an inner atomic block failed")


class TransactionGateway(Protocol):
    def atomic(self) -> AbstractContextManager[None]:
        """Make the writes of the block one transaction.

        Repositories used inside the block do not commit on their own: their
        writes are committed together when the block exits, or all rolled back
        if it raises.

        A nested block joins the enclosing one, without a savepoint: if it
        raises, the whole transaction is doomed. The enclosing block rolls back
        on exit even if the error was caught in between, and then raises
        TransactionRolledBackError rather than pretend it committed.
        """
        ...

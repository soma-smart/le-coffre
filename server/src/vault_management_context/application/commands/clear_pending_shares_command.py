from dataclasses import dataclass


@dataclass(frozen=True)
class ClearPendingSharesCommand:
    """Command to clear all pending shares for vault unlock"""

    pass

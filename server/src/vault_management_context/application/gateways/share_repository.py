from datetime import datetime
from typing import Protocol

from vault_management_context.domain.entities import Share


class ShareRepository(Protocol):
    """Store for the pending unlock shares accumulated before reconstruction.

    A dumb sink regarding *deduplication*: deduplication of shares is enforced upstream by
    ``UnlockVaultUseCase``; repository implementations persist and return what they are given,
    but may still apply storage limits (e.g., an in-memory cap) to bound resource usage.
    """

    def get_all(self) -> list[Share]: ...

    def add(self, shares: list[Share]) -> None: ...

    def clear(self) -> None: ...

    def get_last_share_timestamp(self) -> datetime | None: ...

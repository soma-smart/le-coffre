from datetime import datetime
from typing import Protocol

from vault_management_context.domain.entities import Share


class ShareRepository(Protocol):
    """Store for the pending unlock shares accumulated before reconstruction.

    A dumb sink: deduplication of shares is a domain concern enforced upstream by
    ``UnlockVaultUseCase``; implementations only persist and return what they are given.
    """

    def get_all(self) -> list[Share]: ...

    def add(self, shares: list[Share]) -> None: ...

    def clear(self) -> None: ...

    def get_last_share_timestamp(self) -> datetime | None: ...

from datetime import datetime
from typing import Protocol

from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import UnlockSessionId


class ShareRepository(Protocol):
    """Store for the pending unlock shares accumulated before reconstruction.

    Shares are pooled per unlock session: each session is an independent ceremony, so a
    wrong or malicious share only spoils the session it was submitted to.

    A dumb sink regarding *deduplication*: deduplication of shares is enforced upstream by
    ``UnlockVaultUseCase``; repository implementations persist and return what they are given,
    but may still apply storage limits (e.g., an in-memory cap) to bound resource usage.
    """

    def get_all(self, session_id: UnlockSessionId) -> list[Share]: ...

    def add(self, session_id: UnlockSessionId, shares: list[Share]) -> None: ...

    def clear(self) -> None:
        """Drop the pending shares of every session."""
        ...

    def get_last_share_timestamp(self, session_id: UnlockSessionId) -> datetime | None: ...

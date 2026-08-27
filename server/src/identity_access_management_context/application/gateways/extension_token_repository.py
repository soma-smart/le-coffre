from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import ExtensionToken


class ExtensionTokenRepository(Protocol):
    def add(self, token: ExtensionToken) -> ExtensionToken: ...

    def get_by_token_hash(self, token_hash: str) -> ExtensionToken | None: ...

    def get_by_id(self, token_id: UUID) -> ExtensionToken | None: ...

    def list_for_user(self, user_id: UUID) -> list[ExtensionToken]: ...

    def count_active_for_user(self, user_id: UUID, now: datetime) -> int: ...

    def revoke(self, token_id: UUID, now: datetime) -> bool:
        """Revoke one token. Returns False when it was already revoked.

        Idempotent by design: the WHERE clause keeps a second revoke from
        overwriting the original timestamp, so the audit trail records when
        access actually stopped rather than when someone last clicked.
        """
        ...

    def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        """Revoke every still-active token for a user. Returns how many.

        Called both from the user-facing "revoke all" action and from user
        deletion, alongside the existing one-time-link revocation.
        """
        ...

    def touch_last_used(self, token_id: UUID, now: datetime, coarsen_to_seconds: int) -> None:
        """Best-effort record that the credential was used.

        Coarsened so a busy extension does not write on every request, and it
        must never fail the caller: this is telemetry for the connected-devices
        screen, not part of authentication.
        """
        ...

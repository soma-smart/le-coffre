from dataclasses import dataclass
from uuid import UUID

from notification_context.domain.value_objects import VaultStateChange


@dataclass
class NotifyVaultStateChangedCommand:
    change: VaultStateChange
    # Who locked the vault; None for an unlock, or for a lock caused by a server start.
    locked_by_user_id: UUID | None = None

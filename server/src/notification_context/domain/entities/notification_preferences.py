from dataclasses import dataclass
from uuid import UUID

from notification_context.domain.value_objects.vault_state_change import VaultStateChange


@dataclass
class NotificationPreferences:
    """Which optional emails a user asked for. Everything is off by default."""

    user_id: UUID
    notify_on_vault_lock: bool = False
    notify_on_vault_unlock: bool = False

    def wants(self, change: VaultStateChange) -> bool:
        if change is VaultStateChange.LOCKED:
            return self.notify_on_vault_lock
        return self.notify_on_vault_unlock

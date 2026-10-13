from dataclasses import dataclass
from uuid import UUID


@dataclass
class NotificationPreferences:
    """Which optional emails a user asked for. Everything is off by default."""

    user_id: UUID
    notify_on_vault_lock: bool = False
    notify_on_vault_unlock: bool = False

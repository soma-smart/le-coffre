from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetNotificationPreferencesCommand:
    user_id: UUID


@dataclass
class UpdateNotificationPreferencesCommand:
    user_id: UUID
    notify_on_vault_lock: bool
    notify_on_vault_unlock: bool

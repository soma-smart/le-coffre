from dataclasses import dataclass
from uuid import UUID


@dataclass
class DeleteNotificationPreferencesForDeletedUserCommand:
    user_id: UUID

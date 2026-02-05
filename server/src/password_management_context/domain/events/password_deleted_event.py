from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class PasswordDeletedEvent:
    """Local audit event for password deletion"""

    password_id: UUID
    deleted_by_user_id: UUID
    owner_group_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.deleted_by_user_id

    def to_event_data(self) -> dict:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
        }

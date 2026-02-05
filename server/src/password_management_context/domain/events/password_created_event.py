from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class PasswordCreatedEvent:
    """Local audit event for password creation"""

    password_id: UUID
    password_name: str
    owner_group_id: UUID
    created_by_user_id: UUID
    folder: str
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.created_by_user_id

    def to_event_data(self) -> dict:
        return {
            "password_id": str(self.password_id),
            "password_name": self.password_name,
            "owner_group_id": str(self.owner_group_id),
            "folder": self.folder,
        }

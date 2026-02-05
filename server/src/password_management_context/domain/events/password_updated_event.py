from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class PasswordUpdatedEvent:
    """Local audit event for password update"""

    password_id: UUID
    updated_by_user_id: UUID
    has_name_changed: bool
    has_password_changed: bool
    has_folder_changed: bool
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.updated_by_user_id

    def to_event_data(self) -> dict:
        return {
            "password_id": str(self.password_id),
            "has_name_changed": self.has_name_changed,
            "has_password_changed": self.has_password_changed,
            "has_folder_changed": self.has_folder_changed,
        }

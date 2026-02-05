from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4


class PasswordDeletedEventData(TypedDict):
    """Typed structure for PasswordDeletedEvent storage data"""

    password_id: str
    owner_group_id: str


@dataclass
class PasswordDeletedEvent:
    """Domain event for password deletion"""

    password_id: UUID
    deleted_by_user_id: UUID
    owner_group_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.deleted_by_user_id

    def to_event_data(self) -> PasswordDeletedEventData:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
        }

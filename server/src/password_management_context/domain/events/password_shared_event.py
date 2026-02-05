from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4


class PasswordSharedEventData(TypedDict):
    """Typed structure for PasswordSharedEvent storage data"""

    password_id: str
    owner_group_id: str
    shared_with_group_id: str


@dataclass
class PasswordSharedEvent:
    """Domain event for password sharing"""

    password_id: UUID
    owner_group_id: UUID
    shared_with_group_id: UUID
    shared_by_user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.shared_by_user_id

    def to_event_data(self) -> PasswordSharedEventData:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
            "shared_with_group_id": str(self.shared_with_group_id),
        }

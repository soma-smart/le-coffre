from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4


class PasswordUnsharedEventData(TypedDict):
    """Typed structure for PasswordUnsharedEvent storage data"""

    password_id: str
    owner_group_id: str
    unshared_with_group_id: str


@dataclass
class PasswordUnsharedEvent:
    """Domain event for password unsharing"""

    password_id: UUID
    owner_group_id: UUID
    unshared_with_group_id: UUID
    unshared_by_user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.unshared_by_user_id

    def to_event_data(self) -> PasswordUnsharedEventData:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
            "unshared_with_group_id": str(self.unshared_with_group_id),
        }

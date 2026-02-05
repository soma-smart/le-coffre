from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4


class PasswordAccessedEventData(TypedDict):
    """Typed structure for PasswordAccessedEvent storage data"""

    password_id: str
    password_name: str


@dataclass
class PasswordAccessedEvent:
    """Domain event for password access"""

    password_id: UUID
    password_name: str
    accessed_by_user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    def get_actor_user_id(self) -> UUID:
        return self.accessed_by_user_id

    def to_event_data(self) -> PasswordAccessedEventData:
        return {
            "password_id": str(self.password_id),
            "password_name": self.password_name,
        }

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordAccessedEventData(TypedDict):
    """Typed structure for PasswordAccessedEvent storage data"""

    password_id: str
    password_name: str


@dataclass
class PasswordAccessedEvent(BasePasswordEvent):
    """Domain event for password access"""

    password_name: str
    accessed_by_user_id: UUID

    def get_actor_user_id(self) -> UUID:
        return self.accessed_by_user_id

    def to_event_data(self) -> PasswordAccessedEventData:
        return {
            "password_id": str(self.password_id),
            "password_name": self.password_name,
        }

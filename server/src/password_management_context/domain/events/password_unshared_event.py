from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordUnsharedEventData(TypedDict):
    """Typed structure for PasswordUnsharedEvent storage data"""

    password_id: str
    owner_group_id: str
    unshared_with_group_id: str


@dataclass
class PasswordUnsharedEvent(BasePasswordEvent):
    """Domain event for password unsharing"""

    owner_group_id: UUID
    unshared_with_group_id: UUID
    unshared_by_user_id: UUID

    def get_actor_user_id(self) -> UUID:
        return self.unshared_by_user_id

    def to_event_data(self) -> PasswordUnsharedEventData:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
            "unshared_with_group_id": str(self.unshared_with_group_id),
        }

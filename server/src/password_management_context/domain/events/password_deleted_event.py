from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordDeletedEventData(TypedDict):
    """Typed structure for PasswordDeletedEvent storage data"""

    password_id: str
    owner_group_id: str


@dataclass
class PasswordDeletedEvent(BasePasswordEvent):
    """Domain event for password deletion"""

    deleted_by_user_id: UUID
    owner_group_id: UUID

    def get_actor_user_id(self) -> UUID:
        return self.deleted_by_user_id

    def to_event_data(self) -> PasswordDeletedEventData:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
        }

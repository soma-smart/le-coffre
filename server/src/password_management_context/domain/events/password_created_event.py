from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordCreatedEventData(TypedDict):
    """Typed structure for PasswordCreatedEvent storage data"""

    password_id: str
    password_name: str
    owner_group_id: str
    folder: str
    login: str | None = None
    url: str | None = None


@dataclass
class PasswordCreatedEvent(BasePasswordEvent):
    """Domain event for password creation"""

    password_name: str
    owner_group_id: UUID
    created_by_user_id: UUID
    folder: str
    login: str | None = None
    url: str | None = None

    def get_actor_user_id(self) -> UUID:
        return self.created_by_user_id

    def to_event_data(self) -> PasswordCreatedEventData:
        return {
            "password_id": str(self.password_id),
            "password_name": self.password_name,
            "owner_group_id": str(self.owner_group_id),
            "folder": self.folder,
            "login": self.login,
            "url": self.url,
        }

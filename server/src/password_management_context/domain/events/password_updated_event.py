from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordUpdatedEventData(TypedDict):
    """Typed structure for PasswordUpdatedEvent storage data"""

    password_id: str
    has_name_changed: bool
    has_password_changed: bool
    has_folder_changed: bool
    has_login_changed: bool
    has_url_changed: bool


@dataclass
class PasswordUpdatedEvent(BasePasswordEvent):
    """Domain event for password update"""

    updated_by_user_id: UUID
    has_name_changed: bool
    has_password_changed: bool
    has_folder_changed: bool
    has_login_changed: bool
    has_url_changed: bool

    def get_actor_user_id(self) -> UUID:
        return self.updated_by_user_id

    def to_event_data(self) -> PasswordUpdatedEventData:
        return {
            "password_id": str(self.password_id),
            "has_name_changed": self.has_name_changed,
            "has_password_changed": self.has_password_changed,
            "has_folder_changed": self.has_folder_changed,
            "has_login_changed": self.has_login_changed,
            "has_url_changed": self.has_url_changed,
        }

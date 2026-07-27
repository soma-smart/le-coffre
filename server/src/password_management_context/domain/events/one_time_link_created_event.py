from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class OneTimeLinkCreatedEventData(TypedDict):
    """Typed structure for OneTimeLinkCreatedEvent storage data"""

    password_id: str
    link_id: str
    expires_at: str


@dataclass
class OneTimeLinkCreatedEvent(BasePasswordEvent):
    """Domain event for the generation of a one-time link on a password"""

    link_id: UUID
    expires_at: str
    created_by_user_id: UUID

    def get_actor_user_id(self) -> UUID:
        return self.created_by_user_id

    def to_event_data(self) -> OneTimeLinkCreatedEventData:
        return {
            "password_id": str(self.password_id),
            "link_id": str(self.link_id),
            "expires_at": self.expires_at,
        }

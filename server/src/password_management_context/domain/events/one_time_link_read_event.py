from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class OneTimeLinkReadEventData(TypedDict):
    """Typed structure for OneTimeLinkReadEvent storage data"""

    password_id: str
    link_id: str
    actor: str


@dataclass
class OneTimeLinkReadEvent(BasePasswordEvent):
    """Domain event recording that a one-time link was consumed.

    The reader is anonymous by design, so there is no user to attribute this to.
    The event is filed under the user who generated the link, which is the
    accountable party, and event_data marks the actual reader as anonymous. No
    client IP is recorded.
    """

    link_id: UUID
    created_by_user_id: UUID

    def get_actor_user_id(self) -> UUID:
        return self.created_by_user_id

    def to_event_data(self) -> OneTimeLinkReadEventData:
        return {
            "password_id": str(self.password_id),
            "link_id": str(self.link_id),
            "actor": "anonymous",
        }

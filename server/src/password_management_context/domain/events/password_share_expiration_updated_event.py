from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from .base_password_event import BasePasswordEvent


class PasswordShareExpirationUpdatedEventData(TypedDict):
    """Typed structure for PasswordShareExpirationUpdatedEvent storage data"""

    password_id: str
    owner_group_id: str
    shared_with_group_id: str
    previous_expires_at: str | None
    expires_at: str | None


@dataclass
class PasswordShareExpirationUpdatedEvent(BasePasswordEvent):
    """Domain event for a change to how long an existing share lasts.

    Both dates are kept so the audit trail shows a shortening apart from an
    extension, and a share made permanent (expires_at is None) apart from one
    that never had a deadline.
    """

    owner_group_id: UUID
    shared_with_group_id: UUID
    updated_by_user_id: UUID
    previous_expires_at: str | None = None
    expires_at: str | None = None

    def get_actor_user_id(self) -> UUID:
        return self.updated_by_user_id

    def to_event_data(self) -> PasswordShareExpirationUpdatedEventData:
        return {
            "password_id": str(self.password_id),
            "owner_group_id": str(self.owner_group_id),
            "shared_with_group_id": str(self.shared_with_group_id),
            "previous_expires_at": self.previous_expires_at,
            "expires_at": self.expires_at,
        }

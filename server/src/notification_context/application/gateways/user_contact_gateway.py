from typing import Protocol
from uuid import UUID

from notification_context.domain.value_objects import UserContact


class UserContactGateway(Protocol):
    def get_pairing_notification_recipient(self, user_id: UUID) -> UserContact | None:
        """Who to tell that a browser extension was connected to this account"""
        ...

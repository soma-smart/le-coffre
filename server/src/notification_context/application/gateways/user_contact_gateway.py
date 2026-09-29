from typing import Protocol
from uuid import UUID

from notification_context.domain.value_objects import UserContact


class UserContactGateway(Protocol):
    def get_contact(self, user_id: UUID) -> UserContact | None: ...

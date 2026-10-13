from typing import Protocol
from uuid import UUID

from notification_context.domain.value_objects import Recipient


class RecipientGateway(Protocol):
    def get_recipients(self, user_ids: list[UUID]) -> list[Recipient]:
        """How to reach these users; users that no longer exist are left out"""
        ...

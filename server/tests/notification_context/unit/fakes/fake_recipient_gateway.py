from uuid import UUID

from notification_context.domain.value_objects import Recipient


class FakeRecipientGateway:
    def __init__(self):
        self._recipients: dict[UUID, Recipient] = {}
        self.lookups: list[list[UUID]] = []

    def add(self, recipient: Recipient) -> None:
        self._recipients[recipient.user_id] = recipient

    def get_recipients(self, user_ids: list[UUID]) -> list[Recipient]:
        self.lookups.append(list(user_ids))
        return [self._recipients[user_id] for user_id in user_ids if user_id in self._recipients]

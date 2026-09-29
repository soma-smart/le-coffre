from uuid import UUID

from notification_context.domain.value_objects import UserContact


class FakeUserContactGateway:
    def __init__(self):
        self._contacts: dict[UUID, UserContact] = {}
        self._should_fail = False

    def set_contact(self, user_id: UUID, contact: UserContact) -> None:
        self._contacts[user_id] = contact

    def get_contact(self, user_id: UUID) -> UserContact | None:
        if self._should_fail:
            self._should_fail = False
            raise RuntimeError("simulated lookup failure")
        return self._contacts.get(user_id)

    def fail_next_lookup(self) -> None:
        self._should_fail = True

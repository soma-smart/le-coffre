from uuid import UUID

from notification_context.domain.value_objects import OwnerPromotionNotification


class FakeGroupOwnershipGateway:
    def __init__(self):
        self._details: dict[tuple[UUID, UUID], OwnerPromotionNotification] = {}
        self._should_fail = False

    def set_owner_promotion_details(self, user_id: UUID, group_id: UUID, details: OwnerPromotionNotification) -> None:
        self._details[(user_id, group_id)] = details

    def get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None:
        if self._should_fail:
            raise RuntimeError("simulated lookup failure")
        return self._details.get((user_id, group_id))

    def fail_next_lookup(self) -> None:
        self._should_fail = True

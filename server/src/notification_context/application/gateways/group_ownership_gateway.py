from typing import Protocol
from uuid import UUID

from notification_context.domain.value_objects import OwnerPromotionNotification


class GroupOwnershipGateway(Protocol):
    def get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None: ...

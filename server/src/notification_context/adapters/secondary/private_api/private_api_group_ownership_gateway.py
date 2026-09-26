from uuid import UUID

from identity_access_management_context.adapters.primary.private_api import (
    GroupOwnershipInfoApi,
)
from notification_context.application.gateways import GroupOwnershipGateway
from notification_context.domain.value_objects import OwnerPromotionNotification


class PrivateApiGroupOwnershipGateway(GroupOwnershipGateway):
    """Gateway that wraps IAM's GroupOwnershipInfoApi for the notification context."""

    def __init__(self, group_ownership_info_api: GroupOwnershipInfoApi):
        self._group_ownership_info_api = group_ownership_info_api

    def get_owner_promotion_details(self, user_id: UUID, group_id: UUID) -> OwnerPromotionNotification | None:
        info = self._group_ownership_info_api.get_owner_info(user_id, group_id)
        if info is None:
            return None
        return OwnerPromotionNotification(email=info.email, display_name=info.display_name, group_name=info.group_name)

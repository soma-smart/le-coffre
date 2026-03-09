from uuid import UUID

from identity_access_management_context.application.gateways import GroupUsageGateway
from password_management_context.adapters.primary.private_api import GroupUsageApi


class PrivateApiGroupUsageGateway(GroupUsageGateway):
    """Gateway that wraps password management's GroupUsageApi for group usage checks"""

    def __init__(self, group_usage_api: GroupUsageApi):
        self._group_usage_api = group_usage_api

    def is_group_used(self, group_id: UUID) -> bool:
        """Checks if the group is used in password management context"""
        return self._group_usage_api.is_group_used(group_id)

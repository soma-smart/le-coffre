from uuid import UUID

from notification_context.application.gateways import OneTimeLinkGateway
from notification_context.domain.value_objects import OneTimeLinkDetails
from password_management_context.adapters.primary.private_api import OneTimeLinkInfoApi


class PrivateApiOneTimeLinkGateway(OneTimeLinkGateway):
    """Gateway that wraps the password context's OneTimeLinkInfoApi for the notification context."""

    def __init__(self, one_time_link_info_api: OneTimeLinkInfoApi):
        self._one_time_link_info_api = one_time_link_info_api

    def get_link(self, link_id: UUID) -> OneTimeLinkDetails | None:
        info = self._one_time_link_info_api.get_link(link_id)
        if info is None:
            return None
        return OneTimeLinkDetails(
            link_id=info.link_id,
            created_by_user_id=info.created_by_user_id,
            password_name=info.password_name,
            expires_at=info.expires_at,
            read_at=info.read_at,
            revoked_at=info.revoked_at,
        )

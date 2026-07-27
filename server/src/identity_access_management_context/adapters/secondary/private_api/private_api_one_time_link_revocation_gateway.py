from uuid import UUID

from identity_access_management_context.application.gateways import (
    OneTimeLinkRevocationGateway,
)
from password_management_context.adapters.primary.private_api import (
    OneTimeLinkRevocationApi,
)


class PrivateApiOneTimeLinkRevocationGateway(OneTimeLinkRevocationGateway):
    """Wraps password management's OneTimeLinkRevocationApi for user deletion"""

    def __init__(self, one_time_link_revocation_api: OneTimeLinkRevocationApi):
        self._one_time_link_revocation_api = one_time_link_revocation_api

    def revoke_all_for_user(self, user_id: UUID) -> int:
        return self._one_time_link_revocation_api.revoke_all_for_user(user_id)

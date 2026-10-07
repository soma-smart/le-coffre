from uuid import UUID

from identity_access_management_context.adapters.primary.private_api import UserContactInfoApi
from notification_context.application.gateways import UserContactGateway
from notification_context.domain.value_objects import UserContact


class PrivateApiUserContactGateway(UserContactGateway):
    """Gateway that wraps IAM's UserContactInfoApi for the notification context."""

    def __init__(self, user_contact_info_api: UserContactInfoApi):
        self._user_contact_info_api = user_contact_info_api

    def get_pairing_notification_recipient(self, user_id: UUID) -> UserContact | None:
        info = self._user_contact_info_api.get_contact(user_id)
        if info is None:
            return None
        return UserContact(email=info.email, display_name=info.display_name)

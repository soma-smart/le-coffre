from uuid import UUID

from identity_access_management_context.adapters.primary.private_api import UserContactInfoApi
from notification_context.application.gateways import RecipientGateway
from notification_context.domain.value_objects import Recipient


class PrivateApiRecipientGateway(RecipientGateway):
    """Gateway that wraps IAM's UserContactInfoApi for the notification context."""

    def __init__(self, user_contact_info_api: UserContactInfoApi):
        self._user_contact_info_api = user_contact_info_api

    def get_recipients(self, user_ids: list[UUID]) -> list[Recipient]:
        return [
            Recipient(user_id=contact.user_id, email=contact.email, display_name=contact.display_name)
            for contact in self._user_contact_info_api.get_contacts(user_ids)
        ]

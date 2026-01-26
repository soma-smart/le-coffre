from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
)
from password_management_context.application.responses import PasswordResponse
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.services import PasswordAccessService
from password_management_context.domain.events import (
    PasswordAccessedEvent,
)
from shared_kernel.encryption import EncryptionService
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


class GetPasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        password_access_service: PasswordAccessService,
        event_publisher: DomainEventPublisher,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.password_access_service = password_access_service
        self.event_publisher = event_publisher

    def execute(self, requester_id: UUID, password_id: UUID) -> PasswordResponse:
        password_entity = self.password_repository.get_by_id(password_id)
        if not password_entity:
            raise PasswordNotFoundError(password_id)

        # Check if user has access through their groups and get the group ID
        accessed_through_group_id = self.password_access_service.get_user_access_group(
            requester_id, password_id
        )
        if not accessed_through_group_id:
            raise PasswordAccessDeniedError(requester_id, password_id)

        decrypted_password = self.encryption_service.decrypt(
            password_entity.encrypted_value
        )

        # Publish domain event
        event = PasswordAccessedEvent(
            password_id=password_entity.id,
            password_name=password_entity.name,
            accessed_by_user_id=requester_id,
            accessed_through_group_id=accessed_through_group_id,
        )
        self.event_publisher.publish(event)

        return PasswordResponse(
            id=password_entity.id,
            name=password_entity.name,
            password=decrypted_password,
            folder=password_entity.folder,
        )

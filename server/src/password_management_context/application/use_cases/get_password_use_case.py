import logging
from uuid import UUID

from password_management_context.application.commands import GetPasswordCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
    PasswordEncryptionGateway,
    PasswordEventRepository,
)
from password_management_context.application.responses import PasswordResponse
from password_management_context.application.services import (
    PasswordEventStorageService,
    PasswordTimestampService,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.events import (
    PasswordAccessedEvent,
)
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class GetPasswordUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_encryption_gateway: PasswordEncryptionGateway,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        event_publisher: DomainEventPublisher,
        password_event_repository: PasswordEventRepository,
    ):
        self.password_repository = password_repository
        self.password_encryption_gateway = password_encryption_gateway
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.event_publisher = event_publisher
        self.password_event_repository = password_event_repository

    def execute(self, command: GetPasswordCommand) -> PasswordResponse:
        password_entity = self.password_repository.get_by_id(command.password_id)
        if not password_entity:
            raise PasswordNotFoundError(command.password_id)

        # Check if user has access through their groups
        if not self._user_has_access_through_groups(
            command.requester_id, command.password_id
        ):
            raise PasswordAccessDeniedError(command.requester_id, command.password_id)

        logger.info("Password accessed")
        decrypted_password = self.password_encryption_gateway.decrypt(
            password_entity.encrypted_value
        )

        # Retrieve timestamps using service
        timestamp_service = PasswordTimestampService(self.password_event_repository)
        created_at, last_password_updated_at = timestamp_service.get_timestamps(
            command.password_id
        )

        # Store domain event
        event = PasswordAccessedEvent(
            password_id=password_entity.id,
            password_name=password_entity.name,
            accessed_by_user_id=command.requester_id,
        )
        event_storage_service = PasswordEventStorageService(
            self.password_event_repository
        )
        event_storage_service.store_event(event)

        return PasswordResponse(
            id=password_entity.id,
            name=password_entity.name,
            password=decrypted_password,
            folder=password_entity.folder,
            login=password_entity.login,
            url=password_entity.url,
            created_at=created_at,
            last_password_updated_at=last_password_updated_at,
        )

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user is owner or member of this group
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                # If the group is the owner or has READ permission, user has access
                if is_owner or PasswordPermission.READ in permissions:
                    return True

        return False

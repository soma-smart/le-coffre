from uuid import UUID

from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
    PasswordEncryptionGateway,
    PasswordEventRepository,
)
from password_management_context.application.services import (
    PasswordEventStorageService,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    GroupNotFoundError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.events import (
    PasswordCreatedEvent,
)
from shared_kernel.application.gateways import DomainEventPublisher


from shared_kernel.application.tracing import TracedUseCase


class CreatePasswordUseCase(TracedUseCase):
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

    def execute(self, command: CreatePasswordCommand) -> UUID:
        if not self.group_access_gateway.group_exists(command.group_id):
            raise GroupNotFoundError(command.group_id)

        if not self.group_access_gateway.is_user_owner_of_group(
            command.user_id, command.group_id
        ):
            raise UserNotOwnerOfGroupError(command.user_id, command.group_id)

        encrypted_value = self.password_encryption_gateway.encrypt(
            command.decrypted_password
        )

        password = Password.create(
            id=command.id,
            name=command.name,
            encrypted_value=encrypted_value,
            folder=command.folder,
        )

        self.password_repository.save(password)
        self.password_permissions_repository.set_owner(command.group_id, password.id)

        # Store event in password context (distributed architecture)
        event = PasswordCreatedEvent(
            password_id=password.id,
            password_name=password.name,
            owner_group_id=command.group_id,
            created_by_user_id=command.user_id,
            folder=password.folder,
        )
        event_storage_service = PasswordEventStorageService(
            self.password_event_repository
        )
        event_storage_service.store_event(event)

        return password.id

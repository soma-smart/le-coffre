from uuid import UUID, uuid4

from password_management_context.application.commands.create_password_from_keepass_command import (
    CreatePasswordsFromKeepassCommand,
)
from password_management_context.application.gateways import (
    GroupAccessGateway,
    KeepassReaderGateway,
    PasswordEncryptionGateway,
    PasswordEventRepository,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.services import PasswordEventStorageService
from password_management_context.domain.entities import Password
from password_management_context.domain.events import PasswordCreatedEvent
from password_management_context.domain.exceptions import (
    GroupNotFoundError,
    UserNotOwnerOfGroupError,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase


class CreatePasswordsFromKeepassUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_encryption_gateway: PasswordEncryptionGateway,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        event_publisher: DomainEventPublisher,
        password_event_repository: PasswordEventRepository,
        keepass_reader: KeepassReaderGateway,
    ):
        self.password_repository = password_repository
        self.password_encryption_gateway = password_encryption_gateway
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.event_publisher = event_publisher
        self.password_event_repository = password_event_repository
        self.keepass_reader = keepass_reader

    def execute(self, command: CreatePasswordsFromKeepassCommand) -> list[UUID]:
        if not self.group_access_gateway.group_exists(command.group_id):
            raise GroupNotFoundError(command.group_id)

        if not self.group_access_gateway.is_user_owner_of_group(
            command.user_id,
            command.group_id,
        ):
            raise UserNotOwnerOfGroupError(command.user_id, command.group_id)

        entries = self.keepass_reader.read_entries(
            command.content,
            command.master_password,
        )

        created_ids: list[UUID] = []
        event_storage_service = PasswordEventStorageService(self.password_event_repository)

        for entry in entries:
            password_id = uuid4()

            encrypted_value = self.password_encryption_gateway.encrypt(entry.password or "")

            password = Password.create(
                id=password_id,
                name=entry.title or "Imported password",
                encrypted_value=encrypted_value,
                folder=entry.folder or "keepass_import",
                login=entry.username,
                url=entry.url,
            )

            self.password_repository.save(password)
            self.password_permissions_repository.set_owner(
                command.group_id,
                password.id,
            )

            event = PasswordCreatedEvent(
                password_id=password.id,
                password_name=password.name,
                owner_group_id=command.group_id,
                created_by_user_id=command.user_id,
                folder=password.folder,
                login=password.login,
                url=password.url,
            )
            event_storage_service.store_event(event)

            created_ids.append(password_id)

        return created_ids

from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordEncryptionGateway,
    PasswordEventRepository,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.services import (
    PasswordEventStorageService,
)
from password_management_context.domain.events import (
    PasswordUpdatedEvent,
)
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase


class UpdatePasswordUseCase(TracedUseCase):
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

    def execute(self, new_password: UpdatePasswordCommand) -> None:
        existing_password = self.password_repository.get_by_id(new_password.id)
        if not existing_password:
            raise PasswordNotFoundError(new_password.id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(new_password.id)

        # Find the owner group (there should be exactly one)
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise NotPasswordOwnerError(new_password.requester_id, new_password.id)

        # Check if the user owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(new_password.requester_id, owner_group_id):
            raise UserNotOwnerOfGroupError(new_password.requester_id, owner_group_id)

        # Track what changed
        has_name_changed = False
        has_password_changed = False
        has_folder_changed = False
        has_login_changed = False
        has_url_changed = False

        if new_password.password:
            new_encrypted = self.password_encryption_gateway.encrypt(new_password.password)
            if new_encrypted != existing_password.encrypted_value:
                existing_password.encrypted_value = new_encrypted
                has_password_changed = True

        if new_password.name != existing_password.name:
            existing_password.name = new_password.name
            has_name_changed = True

        previous_folder = existing_password.folder
        existing_password.folder = new_password.folder
        if existing_password.folder != previous_folder:
            has_folder_changed = True

        new_login = new_password.login or None
        if new_login != existing_password.login:
            existing_password.login = new_login
            has_login_changed = True

        new_url = new_password.url or None
        if new_url != existing_password.url:
            existing_password.url = new_url
            has_url_changed = True

        anything_changed = any(
            [
                has_name_changed,
                has_password_changed,
                has_folder_changed,
                has_login_changed,
                has_url_changed,
            ]
        )

        if not anything_changed:
            return

        self.password_repository.update(existing_password)

        event = PasswordUpdatedEvent(
            password_id=existing_password.id,
            updated_by_user_id=new_password.requester_id,
            has_name_changed=has_name_changed,
            has_password_changed=has_password_changed,
            has_folder_changed=has_folder_changed,
            has_login_changed=has_login_changed,
            has_url_changed=has_url_changed,
        )
        event_storage_service = PasswordEventStorageService(self.password_event_repository)
        event_storage_service.store_event(event)

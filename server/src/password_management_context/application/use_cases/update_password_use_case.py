from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.events import (
    PasswordUpdatedEvent,
)
from shared_kernel.encryption import EncryptionService
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


class UpdatePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        event_publisher: DomainEventPublisher,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.event_publisher = event_publisher

    def execute(self, new_password: UpdatePasswordCommand) -> None:
        existing_password = self.password_repository.get_by_id(new_password.id)
        if not existing_password:
            raise PasswordNotFoundError(new_password.id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            new_password.id
        )

        # Find the owner group (there should be exactly one)
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise NotPasswordOwnerError(new_password.requester_id, new_password.id)

        # Check if the user owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(
            new_password.requester_id, owner_group_id
        ):
            raise UserNotOwnerOfGroupError(new_password.requester_id, owner_group_id)

        if new_password.password:
            existing_password.encrypted_value = self.encryption_service.encrypt(
                new_password.password
            )

        if new_password.name:
            existing_password.name = new_password.name

        if new_password.folder:
            existing_password.folder = new_password.folder

        self.password_repository.update(existing_password)

        # Publish domain event
        event = PasswordUpdatedEvent(
            password_id=existing_password.id,
            password_name=existing_password.name,
            updated_by_user_id=new_password.requester_id,
            owner_group_id=owner_group_id,
            folder=existing_password.folder,
        )
        self.event_publisher.publish(event)

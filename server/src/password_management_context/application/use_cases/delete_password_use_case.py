from password_management_context.application.commands import DeletePasswordCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.events import (
    PasswordDeletedEvent,
)
from shared_kernel.application.gateways import DomainEventPublisher


class DeletePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        event_publisher: DomainEventPublisher,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.event_publisher = event_publisher

    def execute(self, command: DeletePasswordCommand) -> None:
        if not self.password_repository.get_by_id(command.password_id):
            raise PasswordNotFoundError(command.password_id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            command.password_id
        )

        # Find the owner group (there should be exactly one)
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise NotPasswordOwnerError(command.requester_id, command.password_id)

        # Check if the user owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(
            command.requester_id, owner_group_id
        ):
            raise UserNotOwnerOfGroupError(command.requester_id, owner_group_id)

        self.password_repository.delete(command.password_id)
        # Revoke all permissions and ownerships for this specific password
        self.password_permissions_repository.revoke_all_access_for_password(
            command.password_id
        )

        # Publish domain event
        event = PasswordDeletedEvent(
            password_id=command.password_id,
            deleted_by_user_id=command.requester_id,
            owner_group_id=owner_group_id,
        )
        self.event_publisher.publish(event)

from password_management_context.application.commands import ShareResourceCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
    GroupNotFoundError,
)
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.domain.events import (
    PasswordSharedEvent,
)
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


class ShareAccessUseCase:
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

    def execute(self, command: ShareResourceCommand):
        # Verify the password exists
        password_entity = self.password_repository.get_by_id(command.password_id)
        if not password_entity:
            raise PasswordNotFoundError(command.password_id)

        # Verify the target group exists
        if not self.group_access_gateway.group_exists(command.group_id):
            raise GroupNotFoundError(command.group_id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            command.password_id
        )

        # Find the owner group
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise PasswordAccessDeniedError(command.owner_id, command.password_id)

        # Check if the requester owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(
            command.owner_id, owner_group_id
        ):
            raise UserNotOwnerOfGroupError(command.owner_id, owner_group_id)

        # Grant READ access to the target group (not setting as owner)
        self.password_permissions_repository.grant_access(
            command.group_id, command.password_id, PasswordPermission.READ
        )

        # Publish domain event
        event = PasswordSharedEvent(
            password_id=command.password_id,
            password_name=password_entity.name,
            shared_with_group_id=command.group_id,
            shared_by_user_id=command.owner_id,
            owner_group_id=owner_group_id,
            can_write=False,  # Currently only READ access
        )
        self.event_publisher.publish(event)

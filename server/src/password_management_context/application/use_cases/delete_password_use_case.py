from uuid import UUID
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
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


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

    def execute(self, requester_id: UUID, password_id: UUID) -> None:
        password_entity = self.password_repository.get_by_id(password_id)
        if not password_entity:
            raise PasswordNotFoundError(password_id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        # Find the owner group (there should be exactly one)
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise NotPasswordOwnerError(requester_id, password_id)

        # Check if the user owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(
            requester_id, owner_group_id
        ):
            raise UserNotOwnerOfGroupError(requester_id, owner_group_id)

        self.password_repository.delete(password_id)

        # Publish domain event
        event = PasswordDeletedEvent(
            password_id=password_id,
            password_name=password_entity.name,
            deleted_by_user_id=requester_id,
            owner_group_id=owner_group_id,
        )
        self.event_publisher.publish(event)

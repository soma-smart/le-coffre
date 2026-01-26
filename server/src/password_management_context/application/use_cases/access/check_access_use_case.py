from uuid import UUID

from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.domain.events import (
    PasswordAccessCheckedEvent,
)
from shared_kernel.access_control import AccessResult, Granted
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


class CheckAccessUseCase:
    def __init__(
        self,
        permission_repository: PasswordPermissionsRepository,
        event_publisher: DomainEventPublisher,
    ):
        self.permission_repository = permission_repository
        self.event_publisher = event_publisher

    def execute(
        self,
        user_id: UUID,
        resource_id: UUID,
        permission: PasswordPermission = PasswordPermission.READ,
    ) -> AccessResult:
        if self.permission_repository.is_owner(user_id, resource_id):
            result = AccessResult(granted=Granted.ACCESS, is_owner=True)
        elif self.permission_repository.has_access(user_id, resource_id, permission):
            result = AccessResult(granted=Granted.ACCESS)
        else:
            result = AccessResult(granted=Granted.NOT_FOUND)

        # Publish domain event
        event = PasswordAccessCheckedEvent(
            password_id=resource_id,
            checked_by_user_id=user_id,
            has_access=result.granted == Granted.ACCESS,
        )
        self.event_publisher.publish(event)

        return result

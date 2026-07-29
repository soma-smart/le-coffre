import logging

from password_management_context.application.commands import ShareResourceCommand
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordEventRepository,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.services import (
    PasswordEventStorageService,
)
from password_management_context.domain.events import (
    PasswordSharedEvent,
)
from password_management_context.domain.exceptions import (
    GroupNotFoundError,
    PasswordAccessDeniedError,
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.value_objects import PasswordPermission, ShareExpiration
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.gateways.time_gateway import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class ShareAccessUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        event_publisher: DomainEventPublisher,
        password_event_repository: PasswordEventRepository,
        time_gateway: TimeGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.event_publisher = event_publisher
        self.password_event_repository = password_event_repository
        self.time_gateway = time_gateway

    def execute(self, command: ShareResourceCommand):
        # Verify the password exists
        if not self.password_repository.get_by_id(command.password_id):
            raise PasswordNotFoundError(command.password_id)

        # Verify the target group exists
        if not self.group_access_gateway.group_exists(command.group_id):
            raise GroupNotFoundError(command.group_id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(command.password_id)

        # Find the owner group
        owner_group_id = None
        for entity_id, access in all_permissions.items():
            if access.is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise PasswordAccessDeniedError(command.owner_id, command.password_id)

        # Check if the requester owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(command.owner_id, owner_group_id):
            raise UserNotOwnerOfGroupError(command.owner_id, owner_group_id)

        expiration = self._validate_expiration(command)
        expires_at = expiration.value if expiration else None

        # Grant READ access to the target group (not setting as owner)
        self.password_permissions_repository.grant_access(
            command.group_id, command.password_id, PasswordPermission.READ, expires_at
        )

        logger.info(
            "Password shared",
            extra={
                "password_id": str(command.password_id),
                "shared_with_group_id": str(command.group_id),
                "by_user_id": str(command.owner_id),
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )

        # Store domain event
        event = PasswordSharedEvent(
            password_id=command.password_id,
            owner_group_id=owner_group_id,
            shared_with_group_id=command.group_id,
            shared_by_user_id=command.owner_id,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        event_storage_service = PasswordEventStorageService(self.password_event_repository)
        event_storage_service.store_event(event)

    def _validate_expiration(self, command: ShareResourceCommand) -> ShareExpiration | None:
        """Reject a deadline that has already passed."""
        if command.expires_at is None:
            return None
        return ShareExpiration.create(
            command.expires_at,
            now=self.time_gateway.get_current_time(),
        )

import logging

from password_management_context.application.commands import UpdateShareExpirationCommand
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordEventRepository,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.services import (
    PasswordEventStorageService,
    PasswordOwnershipService,
)
from password_management_context.domain.events import (
    PasswordShareExpirationUpdatedEvent,
)
from password_management_context.domain.exceptions import (
    ShareNotFoundError,
)
from password_management_context.domain.value_objects import ShareExpiration
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.gateways.time_gateway import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class UpdateShareExpirationUseCase(TracedUseCase):
    """Retimes an existing share: extend it, shorten it, or make it permanent.

    A share that has already lapsed can still be retimed, as long as it has not
    been purged yet. Extending an expired access is the whole point of keeping
    it visible to its owner for a while.
    """

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
        self.ownership_service = PasswordOwnershipService(
            password_repository, password_permissions_repository, group_access_gateway
        )

    def execute(self, command: UpdateShareExpirationCommand) -> None:
        owner_group_id = self.ownership_service.ensure_user_owns_password(command.owner_id, command.password_id)

        previous = self.password_permissions_repository.list_all_permissions_for(command.password_id).get(
            command.group_id
        )
        if previous is None or previous.is_owner:
            raise ShareNotFoundError(command.group_id, command.password_id)

        expiration = self._validate_expiration(command)
        expires_at = expiration.value if expiration else None

        if not self.password_permissions_repository.update_access_expiration(
            command.group_id, command.password_id, expires_at
        ):
            raise ShareNotFoundError(command.group_id, command.password_id)

        logger.info(
            "Password share expiration updated",
            extra={
                "password_id": str(command.password_id),
                "shared_with_group_id": str(command.group_id),
                "by_user_id": str(command.owner_id),
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )

        event = PasswordShareExpirationUpdatedEvent(
            password_id=command.password_id,
            owner_group_id=owner_group_id,
            shared_with_group_id=command.group_id,
            updated_by_user_id=command.owner_id,
            previous_expires_at=previous.expires_at.isoformat() if previous.expires_at else None,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        event_storage_service = PasswordEventStorageService(self.password_event_repository)
        event_storage_service.store_event(event)

    def _validate_expiration(self, command: UpdateShareExpirationCommand) -> ShareExpiration | None:
        """Reject a deadline that has already passed."""
        if command.expires_at is None:
            return None
        return ShareExpiration.create(
            command.expires_at,
            now=self.time_gateway.get_current_time(),
        )

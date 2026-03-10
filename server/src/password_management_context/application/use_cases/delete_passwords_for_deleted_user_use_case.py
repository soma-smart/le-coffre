from uuid import UUID

from password_management_context.application.commands import (
    DeletePasswordsForDeletedUserCommand,
)
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.domain.events import PasswordDeletedEvent
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase


class DeletePasswordsForDeletedUserUseCase(TracedUseCase):
    """
    System-level use case triggered by UserDeletedEvent.
    This is a COMPENSATING action that deletes all passwords owned by a deleted user's personal group.
    NO permission checks - this is a system operation triggered by admin deletion.
    """

    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        event_publisher: DomainEventPublisher,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.event_publisher = event_publisher

    def execute(self, command: DeletePasswordsForDeletedUserCommand) -> None:
        personal_group_id = command.personal_group_id

        # Find all passwords owned by the personal group (for event publishing)
        all_passwords = self.password_repository.list_all()
        password_ids_owned: list[UUID] = []

        for password in all_passwords:
            all_permissions = self.password_permissions_repository.list_all_permissions_for(password.id)

            for entity_id, (is_owner, _) in all_permissions.items():
                if is_owner and entity_id == personal_group_id:
                    password_ids_owned.append(password.id)
                    break

        # Bulk delete all passwords and permissions owned by this group
        self.password_repository.delete_by_owner_group(personal_group_id)
        self.password_permissions_repository.revoke_all_access_for_owner_group(personal_group_id)

        # Publish events for each deleted password (for audit trail)
        for password_id in password_ids_owned:
            event = PasswordDeletedEvent(
                password_id=password_id,
                deleted_by_user_id=command.deleted_by_user_id,
                owner_group_id=personal_group_id,
            )
            self.event_publisher.publish(event)

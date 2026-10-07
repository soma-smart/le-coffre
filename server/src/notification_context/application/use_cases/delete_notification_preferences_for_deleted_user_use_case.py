from notification_context.application.commands import DeleteNotificationPreferencesForDeletedUserCommand
from notification_context.application.gateways import NotificationPreferencesRepository
from shared_kernel.application.tracing import TracedUseCase


class DeleteNotificationPreferencesForDeletedUserUseCase(TracedUseCase):
    """System-level use case triggered by UserDeletedEvent.

    No permission check: the deletion was already authorized in the IAM context.
    """

    def __init__(self, repository: NotificationPreferencesRepository):
        self._repository = repository

    def execute(self, command: DeleteNotificationPreferencesForDeletedUserCommand) -> None:
        self._repository.delete(command.user_id)

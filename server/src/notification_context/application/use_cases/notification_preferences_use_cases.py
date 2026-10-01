from notification_context.application.commands import (
    GetNotificationPreferencesCommand,
    UpdateNotificationPreferencesCommand,
)
from notification_context.application.gateways import NotificationPreferencesRepository
from notification_context.domain.entities import NotificationPreferences
from shared_kernel.application.tracing import TracedUseCase


class GetNotificationPreferencesUseCase(TracedUseCase):
    def __init__(self, repository: NotificationPreferencesRepository):
        self._repository = repository

    def execute(self, command: GetNotificationPreferencesCommand) -> NotificationPreferences:
        return self._repository.get(command.user_id) or NotificationPreferences(user_id=command.user_id)


class UpdateNotificationPreferencesUseCase(TracedUseCase):
    def __init__(self, repository: NotificationPreferencesRepository):
        self._repository = repository

    def execute(self, command: UpdateNotificationPreferencesCommand) -> NotificationPreferences:
        preferences = NotificationPreferences(
            user_id=command.user_id,
            notify_on_vault_lock=command.notify_on_vault_lock,
            notify_on_vault_unlock=command.notify_on_vault_unlock,
        )
        self._repository.save(preferences)
        return preferences

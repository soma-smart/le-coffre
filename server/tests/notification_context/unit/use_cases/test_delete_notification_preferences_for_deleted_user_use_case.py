from uuid import uuid4

from notification_context.application.commands import DeleteNotificationPreferencesForDeletedUserCommand
from notification_context.application.use_cases import DeleteNotificationPreferencesForDeletedUserUseCase
from notification_context.domain.entities import NotificationPreferences


def test_given_deleted_user_should_drop_only_their_preferences(preferences_repository):
    deleted, kept = uuid4(), uuid4()
    preferences_repository.save(NotificationPreferences(user_id=deleted, notify_on_vault_lock=True))
    preferences_repository.save(NotificationPreferences(user_id=kept, notify_on_vault_lock=True))

    DeleteNotificationPreferencesForDeletedUserUseCase(preferences_repository).execute(
        DeleteNotificationPreferencesForDeletedUserCommand(user_id=deleted)
    )

    assert preferences_repository.get(deleted) is None
    assert preferences_repository.list_user_ids_to_notify_on_lock() == [kept]


def test_given_user_without_preferences_should_do_nothing(preferences_repository):
    DeleteNotificationPreferencesForDeletedUserUseCase(preferences_repository).execute(
        DeleteNotificationPreferencesForDeletedUserCommand(user_id=uuid4())
    )

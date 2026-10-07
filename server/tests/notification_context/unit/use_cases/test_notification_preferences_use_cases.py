from uuid import uuid4

from notification_context.application.commands import (
    GetNotificationPreferencesCommand,
    UpdateNotificationPreferencesCommand,
)
from notification_context.application.use_cases import (
    GetNotificationPreferencesUseCase,
    UpdateNotificationPreferencesUseCase,
)


def test_given_user_without_preferences_when_getting_them_should_have_every_notification_off(
    preferences_repository,
):
    user_id = uuid4()

    preferences = GetNotificationPreferencesUseCase(preferences_repository).execute(
        GetNotificationPreferencesCommand(user_id=user_id)
    )

    assert preferences.user_id == user_id
    assert preferences.notify_on_vault_lock is False
    assert preferences.notify_on_vault_unlock is False


def test_given_updated_preferences_when_getting_them_should_return_the_update(preferences_repository):
    user_id = uuid4()

    UpdateNotificationPreferencesUseCase(preferences_repository).execute(
        UpdateNotificationPreferencesCommand(user_id=user_id, notify_on_vault_lock=True, notify_on_vault_unlock=False)
    )
    preferences = GetNotificationPreferencesUseCase(preferences_repository).execute(
        GetNotificationPreferencesCommand(user_id=user_id)
    )

    assert preferences.notify_on_vault_lock is True
    assert preferences.notify_on_vault_unlock is False

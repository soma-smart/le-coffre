from uuid import UUID

from notification_context.domain.entities import NotificationPreferences


class FakeNotificationPreferencesRepository:
    def __init__(self):
        self._preferences: dict[UUID, NotificationPreferences] = {}

    def get(self, user_id: UUID) -> NotificationPreferences | None:
        return self._preferences.get(user_id)

    def save(self, preferences: NotificationPreferences) -> None:
        self._preferences[preferences.user_id] = preferences

    def delete(self, user_id: UUID) -> None:
        self._preferences.pop(user_id, None)

    def list_user_ids_to_notify_on_lock(self) -> list[UUID]:
        return [p.user_id for p in self._preferences.values() if p.notify_on_vault_lock]

    def list_user_ids_to_notify_on_unlock(self) -> list[UUID]:
        return [p.user_id for p in self._preferences.values() if p.notify_on_vault_unlock]

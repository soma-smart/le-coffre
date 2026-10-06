from uuid import UUID

from notification_context.domain.entities import NotificationPreferences
from notification_context.domain.value_objects import VaultStateChange


class FakeNotificationPreferencesRepository:
    def __init__(self):
        self._preferences: dict[UUID, NotificationPreferences] = {}

    def get(self, user_id: UUID) -> NotificationPreferences | None:
        return self._preferences.get(user_id)

    def save(self, preferences: NotificationPreferences) -> None:
        self._preferences[preferences.user_id] = preferences

    def list_user_ids_to_notify(self, change: VaultStateChange) -> list[UUID]:
        return [p.user_id for p in self._preferences.values() if p.wants(change)]

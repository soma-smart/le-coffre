from typing import Protocol
from uuid import UUID

from notification_context.domain.entities import NotificationPreferences
from notification_context.domain.value_objects import VaultStateChange


class NotificationPreferencesRepository(Protocol):
    def get(self, user_id: UUID) -> NotificationPreferences | None: ...

    def save(self, preferences: NotificationPreferences) -> None:
        """Insert or replace the preferences of preferences.user_id"""
        ...

    def list_user_ids_to_notify(self, change: VaultStateChange) -> list[UUID]:
        """Users who asked to be emailed about this vault state change"""
        ...

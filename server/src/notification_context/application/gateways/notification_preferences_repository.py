from typing import Protocol
from uuid import UUID

from notification_context.domain.entities import NotificationPreferences


class NotificationPreferencesRepository(Protocol):
    def get(self, user_id: UUID) -> NotificationPreferences | None: ...

    def save(self, preferences: NotificationPreferences) -> None:
        """Insert or replace the preferences of preferences.user_id"""
        ...

    def delete(self, user_id: UUID) -> None:
        """Remove user_id's preferences, if any"""
        ...

    def list_user_ids_to_notify_on_lock(self) -> list[UUID]:
        """Users who asked to be emailed when the vault gets locked"""
        ...

    def list_user_ids_to_notify_on_unlock(self) -> list[UUID]:
        """Users who asked to be emailed when the vault gets unlocked"""
        ...

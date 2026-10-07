from pydantic import BaseModel

from notification_context.domain.entities import NotificationPreferences


class NotificationPreferencesResponse(BaseModel):
    notify_on_vault_lock: bool
    notify_on_vault_unlock: bool

    @classmethod
    def from_preferences(cls, preferences: NotificationPreferences) -> "NotificationPreferencesResponse":
        return cls(
            notify_on_vault_lock=preferences.notify_on_vault_lock,
            notify_on_vault_unlock=preferences.notify_on_vault_unlock,
        )

from uuid import UUID

from sqlmodel import Session, col, select

from notification_context.adapters.secondary.sql.notification_preference_model import (
    NotificationPreferenceTable,
)
from notification_context.application.gateways import NotificationPreferencesRepository
from notification_context.domain.entities import NotificationPreferences
from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository


class SqlNotificationPreferencesRepository(SQLBaseRepository, NotificationPreferencesRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def get(self, user_id: UUID) -> NotificationPreferences | None:
        row = self._session.get(NotificationPreferenceTable, user_id)
        if row is None:
            return None
        return NotificationPreferences(
            user_id=row.user_id,
            notify_on_vault_lock=row.notify_on_vault_lock,
            notify_on_vault_unlock=row.notify_on_vault_unlock,
        )

    def save(self, preferences: NotificationPreferences) -> None:
        row = self._session.get(NotificationPreferenceTable, preferences.user_id)
        if row is None:
            row = NotificationPreferenceTable(user_id=preferences.user_id)
        row.notify_on_vault_lock = preferences.notify_on_vault_lock
        row.notify_on_vault_unlock = preferences.notify_on_vault_unlock
        self._session.add(row)
        self.commit()

    def delete(self, user_id: UUID) -> None:
        row = self._session.get(NotificationPreferenceTable, user_id)
        if row is None:
            return
        self._session.delete(row)
        self.commit()

    def list_user_ids_to_notify_on_lock(self) -> list[UUID]:
        statement = select(NotificationPreferenceTable.user_id).where(
            col(NotificationPreferenceTable.notify_on_vault_lock).is_(True)
        )
        return list(self._session.exec(statement).all())

    def list_user_ids_to_notify_on_unlock(self) -> list[UUID]:
        statement = select(NotificationPreferenceTable.user_id).where(
            col(NotificationPreferenceTable.notify_on_vault_unlock).is_(True)
        )
        return list(self._session.exec(statement).all())

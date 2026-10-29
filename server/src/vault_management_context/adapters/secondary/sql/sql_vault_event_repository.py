from datetime import datetime
from uuid import UUID

from sqlmodel import Session, col, select

from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository
from shared_kernel.utils import as_utc
from vault_management_context.adapters.secondary.sql.models.vault_event import (
    VaultEventTable,
)
from vault_management_context.domain.value_objects import StoredVaultEvent


class SqlVaultEventRepository(SQLBaseRepository):
    """SQL implementation of vault event repository"""

    def __init__(self, session: Session):
        super().__init__(session)

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        """Append a vault event to storage"""
        event = VaultEventTable(
            event_id=event_id,
            event_type=event_type,
            occurred_on=occurred_on,
            actor_user_id=actor_user_id,
            event_data=event_data,
        )
        self._session.add(event)
        self.commit()

    def get_last_event_type(self, event_types: list[str]) -> str | None:
        statement = (
            select(VaultEventTable.event_type)
            .where(col(VaultEventTable.event_type).in_(event_types))
            .order_by(col(VaultEventTable.occurred_on).desc())
            .limit(1)
        )
        return self._session.exec(statement).first()

    def list_events(self, event_types: list[str]) -> list[StoredVaultEvent]:
        statement = (
            select(VaultEventTable)
            .where(col(VaultEventTable.event_type).in_(event_types))
            .order_by(col(VaultEventTable.occurred_on))
        )
        return [
            StoredVaultEvent(
                event_type=row.event_type,
                occurred_on=as_utc(row.occurred_on),  # type: ignore[arg-type]
                event_data=dict(row.event_data or {}),
            )
            for row in self._session.exec(statement).all()
        ]

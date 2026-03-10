from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository
from vault_management_context.adapters.secondary.sql.models.vault_event import (
    VaultEventTable,
)


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

from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.adapters.secondary.sql.model.iam_event import (
    IamEventTable,
)
from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository


class SqlIamEventRepository(SQLBaseRepository):
    """SQL implementation of IAM event repository"""

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
        """Append an IAM event to storage"""
        event = IamEventTable(
            event_id=event_id,
            event_type=event_type,
            occurred_on=occurred_on,
            actor_user_id=actor_user_id,
            event_data=event_data,
        )
        self._session.add(event)
        self.commit()

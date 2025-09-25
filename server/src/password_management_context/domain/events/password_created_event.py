from uuid import UUID, uuid4
from typing import Optional
from datetime import datetime, UTC
from shared_kernel.pubsub import DomainEvent


class PasswordCreatedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        created_by: UUID,
        name: str,
        folder: Optional[str],
        event_id: UUID,
        occurred_on: datetime,
    ):
        super().__init__(event_id, occurred_on)
        self.password_id = password_id
        self.created_by = created_by
        self.name = name
        self.folder = folder

    @classmethod
    def create(
        cls,
        password_id: UUID,
        created_by: UUID,
        name: str,
        folder: Optional[str] = None,
    ) -> "PasswordCreatedEvent":
        return cls(
            password_id=password_id,
            created_by=created_by,
            name=name,
            folder=folder,
            event_id=uuid4(),
            occurred_on=datetime.now(UTC),
        )

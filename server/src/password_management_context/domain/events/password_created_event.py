from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class PasswordCreatedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        password_name: str,
        owner_group_id: UUID,
        created_by_user_id: UUID,
        folder: str | None = None,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.password_id = password_id
        self.password_name = password_name
        self.owner_group_id = owner_group_id
        self.created_by_user_id = created_by_user_id
        self.folder = folder

    @property
    def bounded_context(self) -> str:
        return "password_management"

    @property
    def actor_user_id(self) -> UUID:
        return self.created_by_user_id

    @property
    def target_entity_id(self) -> UUID:
        return self.password_id

    @property
    def target_entity_type(self) -> str:
        return "password"

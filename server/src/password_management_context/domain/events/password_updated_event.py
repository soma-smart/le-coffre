from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class PasswordUpdatedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        updated_by_user_id: UUID,
        has_name_changed: bool,
        has_password_changed: bool,
        has_folder_changed: bool,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.MEDIUM,
        )
        self.password_id = password_id
        self.updated_by_user_id = updated_by_user_id
        self.has_name_changed = has_name_changed
        self.has_password_changed = has_password_changed
        self.has_folder_changed = has_folder_changed

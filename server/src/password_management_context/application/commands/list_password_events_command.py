from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ListPasswordEventsCommand:
    password_id: UUID
    user_id: UUID
    event_types: list[str] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

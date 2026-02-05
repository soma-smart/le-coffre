"""Protocol for password events that can be stored in event log"""

from typing import Protocol
from uuid import UUID
from datetime import datetime


class StorablePasswordEvent(Protocol):
    """Protocol for events that can be stored in password event log"""

    event_id: UUID
    occurred_on: datetime
    password_id: UUID

    def get_actor_user_id(self) -> UUID:
        """Get the user who performed the action"""
        ...

    def to_event_data(self) -> dict:
        """Convert event to storage dictionary"""
        ...

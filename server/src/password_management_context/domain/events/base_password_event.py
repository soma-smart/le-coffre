"""Base class for all password domain events"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class BasePasswordEvent(ABC):
    """Abstract base class for password domain events"""

    password_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    # UTC, like IamEvent: the admin activity feed merges both tables in one order,
    # and a local clock would misplace these events on a server that is not in UTC.
    occurred_on: datetime = field(default_factory=lambda: datetime.now(UTC))

    @abstractmethod
    def get_actor_principal_id(self) -> UUID:
        """Return the user ID who triggered this event"""
        ...

    @abstractmethod
    def to_event_data(self) -> dict[str, Any]:
        """Convert event to storage-ready dictionary"""
        ...

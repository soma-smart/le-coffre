"""Base class for all password domain events"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class BasePasswordEvent(ABC):
    """Abstract base class for password domain events"""

    password_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

    @abstractmethod
    def get_actor_user_id(self) -> UUID:
        """Return the user ID who triggered this event"""
        ...

    @abstractmethod
    def to_event_data(self) -> dict[str, Any]:
        """Convert event to storage-ready dictionary"""
        ...

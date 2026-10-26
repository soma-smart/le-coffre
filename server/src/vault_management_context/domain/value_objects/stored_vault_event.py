from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class StoredVaultEvent:
    """A vault audit record as read back from storage."""

    event_type: str
    occurred_on: datetime
    event_data: dict = field(default_factory=dict)

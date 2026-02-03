from dataclasses import dataclass
from datetime import datetime

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ListEventCommand:
    requesting_user: AuthenticatedUser
    event_types: list[str] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ListOneTimeLinksCommand:
    password_id: UUID
    requesting_user_id: UUID
    # Active links are what the owner can still act on; the rest is history and
    # is only fetched when explicitly asked for.
    include_inactive: bool = False

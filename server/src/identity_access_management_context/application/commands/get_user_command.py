from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetUserCommand:
    user_id: UUID | None = None
    user_email: str | None = None

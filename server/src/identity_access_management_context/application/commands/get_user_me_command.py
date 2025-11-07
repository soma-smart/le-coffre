from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetUserMeCommand:
    user_id: UUID
    requesting_user_id: UUID

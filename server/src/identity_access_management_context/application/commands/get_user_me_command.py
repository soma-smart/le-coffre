from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetUserMeCommand:
    requesting_user_id: UUID

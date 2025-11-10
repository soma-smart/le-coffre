from dataclasses import dataclass
from uuid import UUID
from typing import List


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    roles: List[str]

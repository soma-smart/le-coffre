from dataclasses import dataclass
from uuid import UUID
from typing import List


@dataclass
class GetUserMeResponse:
    id: UUID
    username: str
    email: str
    name: str
    roles: List[str]
    is_sso: bool

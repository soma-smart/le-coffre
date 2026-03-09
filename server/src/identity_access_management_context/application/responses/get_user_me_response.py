from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetUserMeResponse:
    id: UUID
    username: str
    email: str
    name: str
    roles: list[str]
    is_sso: bool

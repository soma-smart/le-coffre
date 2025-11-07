from dataclasses import dataclass
from uuid import UUID


@dataclass
class LoginResponse:
    access_token: str
    refresh_token: str
    user_id: UUID
    email: str

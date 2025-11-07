from dataclasses import dataclass
from uuid import UUID


@dataclass
class AdminLoginResponse:
    jwt_token: str
    refresh_token: str
    admin_id: UUID
    email: str

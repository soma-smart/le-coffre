from dataclasses import dataclass
from uuid import UUID


@dataclass
class SsoLoginResponse:
    jwt_token: str
    refresh_token: str
    user_id: UUID
    email: str
    display_name: str
    is_new_user: bool

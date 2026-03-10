from dataclasses import dataclass
from uuid import UUID


@dataclass
class ValidateUserTokenResponse:
    is_valid: bool
    user_id: UUID
    email: str
    display_name: str
    roles: list[str]

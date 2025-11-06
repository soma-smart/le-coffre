from dataclasses import dataclass
from uuid import UUID
from typing import List


@dataclass
class ValidateUserTokenResponse:
    is_valid: bool
    user_id: UUID
    email: str
    display_name: str
    session_id: UUID
    roles: List[str]

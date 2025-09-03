from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AuthenticateWithSSOResponse:
    jwt_token: str
    external_user_id: str
    email: str
    display_name: str
    provider: str
    claims: Dict[str, Any]

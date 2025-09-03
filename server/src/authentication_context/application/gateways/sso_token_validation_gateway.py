from typing import Dict, Any, Protocol
from dataclasses import dataclass


@dataclass
class SSOValidationResult:
    is_valid: bool
    external_user_id: str
    email: str
    display_name: str
    provider: str
    claims: Dict[str, Any]


class SSOTokenValidationGateway(Protocol):
    async def validate_token(
        self, token: str, provider: str
    ) -> SSOValidationResult: ...

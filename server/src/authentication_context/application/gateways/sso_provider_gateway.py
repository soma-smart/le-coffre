from dataclasses import dataclass
from typing import Dict, Any, Protocol


@dataclass
class SSOValidationResult:
    is_valid: bool
    external_user_id: str
    email: str
    display_name: str
    provider: str
    claims: Dict[str, Any]


class SSOProviderGateway(Protocol):
    async def get_authorization_url(self, state: str) -> str:
        """Generate the authorization URL to redirect users to the SSO provider"""
        ...

    async def validate_token(self, token: str) -> SSOValidationResult:
        """Validate the token received from the SSO provider"""
        ...

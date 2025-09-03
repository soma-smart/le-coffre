from typing import Dict, Any, Optional
from authentication_context.application.gateways import (
    SSOProviderGateway,
    SSOValidationResult,
)


class FakeSSOProviderGateway(SSOProviderGateway):
    def __init__(self):
        self.valid_tokens = {}
        self.validation_calls = []
        self.authorization_calls = []

    def set_provider_name(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def set_valid_token(
        self,
        token: str,
        external_user_id: str,
        email: str,
        display_name: str,
        claims: Optional[Dict[str, Any]] = None,
    ):
        if claims is None:
            claims = {}
        self.valid_tokens[token] = SSOValidationResult(
            is_valid=True,
            external_user_id=external_user_id,
            email=email,
            display_name=display_name,
            provider=self.provider_name,
            claims=claims,
        )

    async def get_authorization_url(self, state: str) -> str:
        self.authorization_calls.append(state)
        return f"https://{self.provider_name}.com/oauth/authorize?state={state}&client_id=fake_client&redirect_uri=http://localhost/callback"

    async def validate_token(self, token: str) -> SSOValidationResult:
        self.validation_calls.append(token)

        if token in self.valid_tokens:
            return self.valid_tokens[token]

        return SSOValidationResult(
            is_valid=False,
            external_user_id="",
            email="",
            display_name="",
            provider=self.provider_name,
            claims={},
        )

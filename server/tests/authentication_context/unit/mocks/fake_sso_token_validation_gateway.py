from typing import Dict, Any, Optional
from authentication_context.application.gateways import (
    SSOTokenValidationGateway,
    SSOValidationResult,
)


class FakeSSOTokenValidationGateway(SSOTokenValidationGateway):
    def __init__(self):
        self.valid_tokens = {}
        self.validation_calls = []

    def set_valid_token(
        self,
        token: str,
        provider: str,
        external_user_id: str,
        email: str,
        display_name: str,
        claims: Optional[Dict[str, Any]] = None,
    ):
        if claims is None:
            claims = {}
        self.valid_tokens[(token, provider)] = SSOValidationResult(
            is_valid=True,
            external_user_id=external_user_id,
            email=email,
            display_name=display_name,
            provider=provider,
            claims=claims,
        )

    async def validate_token(self, token: str, provider: str) -> SSOValidationResult:
        self.validation_calls.append((token, provider))

        if (token, provider) in self.valid_tokens:
            return self.valid_tokens[(token, provider)]

        return SSOValidationResult(
            is_valid=False,
            external_user_id="",
            email="",
            display_name="",
            provider=provider,
            claims={},
        )

from authentication_context.application.commands import (
    AuthenticateWithSSOCommand,
)
from authentication_context.application.responses import (
    AuthenticateWithSSOResponse,
)
from authentication_context.application.gateways.sso_provider_gateway import (
    SSOProviderGateway,
)
from authentication_context.application.gateways import (
    JWTTokenGateway,
)
from authentication_context.domain.exceptions import InvalidSSOTokenException


class AuthenticateWithSSOUseCase:
    def __init__(
        self,
        sso_provider_gateway: SSOProviderGateway,
        jwt_token_gateway: JWTTokenGateway,
    ):
        self.sso_provider_gateway = sso_provider_gateway
        self.jwt_token_gateway = jwt_token_gateway

    async def execute(
        self, command: AuthenticateWithSSOCommand
    ) -> AuthenticateWithSSOResponse:
        validation_result = await self.sso_provider_gateway.validate_token(
            command.token
        )

        if not validation_result.is_valid:
            raise InvalidSSOTokenException("Invalid SSO token provided")

        jwt_token = await self.jwt_token_gateway.generate_token(
            user_id=validation_result.external_user_id, claims=validation_result.claims
        )

        return AuthenticateWithSSOResponse(
            jwt_token=jwt_token,
            external_user_id=validation_result.external_user_id,
            email=validation_result.email,
            display_name=validation_result.display_name,
            provider=validation_result.provider,
            claims=validation_result.claims,
        )

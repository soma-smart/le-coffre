from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.responses import (
    RefreshAccessTokenResponse,
)
from identity_access_management_context.application.gateways import (
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from shared_kernel.application.gateways import TimeGateway


class RefreshAccessTokenUseCase:
    def __init__(
        self,
        token_gateway: TokenGateway,
        user_repository: UserRepository,
        time_provider: TimeGateway,
    ):
        self.token_gateway = token_gateway
        self.user_repository = user_repository
        self.time_provider = time_provider

    async def execute(
        self, command: RefreshAccessTokenCommand
    ) -> RefreshAccessTokenResponse:
        token_data = await self.token_gateway.validate_refresh_token(
            command.refresh_token
        )

        if token_data is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        user = self.user_repository.get_by_id(token_data.user_id)
        if user is None:
            raise InvalidRefreshTokenException("User no longer exists")

        # Revoke the old refresh token before issuing a new one
        await self.token_gateway.revoke_refresh_token(command.refresh_token)

        new_access_token = await self.token_gateway.generate_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )

        new_refresh_token = await self.token_gateway.generate_refresh_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )

        return RefreshAccessTokenResponse(
            access_token=new_access_token.value,
            refresh_token=new_refresh_token,
            user_id=token_data.user_id,
        )

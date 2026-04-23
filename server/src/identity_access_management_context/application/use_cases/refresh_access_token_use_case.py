from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.gateways import (
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    RefreshAccessTokenResponse,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)


class RefreshAccessTokenUseCase(TracedUseCase):
    def __init__(
        self,
        token_gateway: TokenGateway,
        user_repository: UserRepository,
        time_provider: TimeGateway,
    ):
        self.token_gateway = token_gateway
        self.user_repository = user_repository
        self.time_provider = time_provider

    def execute(self, command: RefreshAccessTokenCommand) -> RefreshAccessTokenResponse:
        token_data = self.token_gateway.validate_refresh_token(command.refresh_token)

        if token_data is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        user = self.user_repository.get_by_id(token_data.user_id)
        if user is None:
            raise InvalidRefreshTokenException("User no longer exists")

        new_access_token = self.token_gateway.generate_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )

        return RefreshAccessTokenResponse(
            access_token=new_access_token.value,
            user_id=token_data.user_id,
        )

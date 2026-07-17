from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.gateways import (
    RevokedTokenRepository,
    TokenGateway,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    RefreshAccessTokenResponse,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class RefreshAccessTokenUseCase(TracedUseCase):
    def __init__(
        self,
        token_gateway: TokenGateway,
        user_repository: UserRepository,
        revoked_token_repository: RevokedTokenRepository,
        time_provider: TimeGateway,
    ):
        self.token_gateway = token_gateway
        self.user_repository = user_repository
        self.revoked_token_repository = revoked_token_repository
        self.time_provider = time_provider

    def execute(self, command: RefreshAccessTokenCommand) -> RefreshAccessTokenResponse:
        token_data = self.token_gateway.validate_refresh_token(command.refresh_token)

        if token_data is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        user = self.user_repository.get_by_id(token_data.user_id)
        if user is None:
            raise InvalidRefreshTokenException("User no longer exists")

        now = self.time_provider.get_current_time()
        if token_data.jti and self.revoked_token_repository.is_revoked(token_data.jti, now):
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        if user.session_invalid_before is not None and token_data.issued_at is not None:
            session_cutoff = user.session_invalid_before.replace(microsecond=0)
            if token_data.issued_at < session_cutoff:
                raise InvalidRefreshTokenException("Invalid or expired refresh token")

        if user.current_refresh_token_jti != token_data.jti:
            self.revoked_token_repository.revoke(token_data, "refresh_token_reuse_detected", now)
            user.current_refresh_token_jti = None
            user.session_invalid_before = now
            self.user_repository.update(user)
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        new_access_token = self.token_gateway.generate_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )
        new_refresh_token = self.token_gateway.generate_refresh_token(
            user_id=token_data.user_id,
            email=token_data.email,
            roles=user.roles,
        )
        self.revoked_token_repository.revoke(token_data, "refresh_token_rotated", now)
        user.current_refresh_token_jti = new_refresh_token.jti
        self.user_repository.update(user)

        return RefreshAccessTokenResponse(
            access_token=new_access_token.value,
            refresh_token=new_refresh_token.value,
            user_id=token_data.user_id,
        )

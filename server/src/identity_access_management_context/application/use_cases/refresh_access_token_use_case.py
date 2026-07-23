from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.gateways import (
    AuthSessionRepository,
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
        auth_session_repository: AuthSessionRepository,
        revoked_token_repository: RevokedTokenRepository,
        time_provider: TimeGateway,
    ):
        self.token_gateway = token_gateway
        self.user_repository = user_repository
        self.auth_session_repository = auth_session_repository
        self.revoked_token_repository = revoked_token_repository
        self.time_provider = time_provider

    def execute(self, command: RefreshAccessTokenCommand) -> RefreshAccessTokenResponse:
        token_data = self.token_gateway.validate_refresh_token(command.refresh_token)

        if token_data is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        user = self.user_repository.get_by_id(token_data.user_id)
        if user is None:
            raise InvalidRefreshTokenException("User no longer exists")

        if token_data.jti is None or token_data.issued_at is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        now = self.time_provider.get_current_time()
        self.revoked_token_repository.purge_expired(now)
        if self.revoked_token_repository.is_revoked(token_data.jti, now):
            raise InvalidRefreshTokenException("Invalid or expired refresh token")

        if user.session_invalid_before is not None:
            session_cutoff = user.session_invalid_before
            if token_data.issued_at < session_cutoff:
                raise InvalidRefreshTokenException("Invalid or expired refresh token")

        session = self.auth_session_repository.get_active_by_user_id_and_refresh_jti(
            user_id=token_data.user_id,
            refresh_token_jti=token_data.jti,
        )
        if session is None:
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
        if new_refresh_token.jti is None:
            raise InvalidRefreshTokenException("Invalid or expired refresh token")
        self.auth_session_repository.rotate_refresh_token_jti(
            session_id=session.id,
            new_refresh_token_jti=new_refresh_token.jti,
            rotated_at=now,
        )

        return RefreshAccessTokenResponse(
            access_token=new_access_token.value,
            refresh_token=new_refresh_token.value,
            user_id=token_data.user_id,
        )

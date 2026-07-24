from identity_access_management_context.application.commands import LogoutCommand
from identity_access_management_context.application.gateways import (
    REVOCATION_REASON_LOGOUT,
    AuthSessionRepository,
    RevokedTokenRepository,
    TokenGateway,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class LogoutUseCase(TracedUseCase):
    def __init__(
        self,
        token_gateway: TokenGateway,
        revoked_token_repository: RevokedTokenRepository,
        auth_session_repository: AuthSessionRepository,
        time_provider: TimeGateway,
    ):
        self._token_gateway = token_gateway
        self._revoked_token_repository = revoked_token_repository
        self._auth_session_repository = auth_session_repository
        self._time_provider = time_provider

    def execute(self, command: LogoutCommand) -> None:
        now = self._time_provider.get_current_time()
        self._revoked_token_repository.purge_expired(now)

        access_token = None
        if command.access_token:
            access_token = self._token_gateway.validate_token(command.access_token)
        refresh_token = self._token_gateway.validate_refresh_token(command.refresh_token)

        if access_token is not None:
            self._revoked_token_repository.revoke(access_token, REVOCATION_REASON_LOGOUT, now)

        if refresh_token is not None:
            self._revoked_token_repository.revoke(refresh_token, REVOCATION_REASON_LOGOUT, now)
            if refresh_token.jti is not None:
                self._auth_session_repository.invalidate_by_user_id_and_refresh_jti(
                    user_id=refresh_token.user_id,
                    refresh_token_jti=refresh_token.jti,
                    invalidated_at=now,
                )

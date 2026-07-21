from identity_access_management_context.application.commands import LogoutCommand
from identity_access_management_context.application.gateways import (
    RevokedTokenRepository,
    TokenGateway,
    UserRepository,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class LogoutUseCase(TracedUseCase):
    def __init__(
        self,
        token_gateway: TokenGateway,
        revoked_token_repository: RevokedTokenRepository,
        user_repository: UserRepository,
        time_provider: TimeGateway,
    ):
        self._token_gateway = token_gateway
        self._revoked_token_repository = revoked_token_repository
        self._user_repository = user_repository
        self._time_provider = time_provider

    def execute(self, command: LogoutCommand) -> None:
        now = self._time_provider.get_current_time()
        self._revoked_token_repository.purge_expired(now)

        access_token = self._token_gateway.validate_token(command.access_token) if command.access_token else None
        refresh_token = (
            self._token_gateway.validate_refresh_token(command.refresh_token) if command.refresh_token else None
        )

        if access_token is not None:
            self._revoked_token_repository.revoke(access_token, "logout", now)

        if refresh_token is not None:
            self._revoked_token_repository.revoke(refresh_token, "logout", now)

        user_id = access_token.user_id if access_token is not None else None
        if user_id is None and refresh_token is not None:
            user_id = refresh_token.user_id

        if user_id is None:
            return

        user = self._user_repository.get_by_id(user_id)
        if user is None:
            return

        user.current_refresh_token_jti = None
        self._user_repository.update(user)

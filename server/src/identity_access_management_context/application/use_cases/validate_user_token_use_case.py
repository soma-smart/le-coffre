from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.gateways import (
    RevokedTokenRepository,
    SsoUserRepository,
    TokenGateway,
    UserPasswordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    ValidateUserTokenResponse,
)
from identity_access_management_context.domain.exceptions import (
    InsufficientRoleException,
    InvalidTokenException,
    UserNotFoundException,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class ValidateUserTokenUseCase(TracedUseCase):
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        token_gateway: TokenGateway,
        sso_user_repository: SsoUserRepository,
        user_repository: UserRepository,
        revoked_token_repository: RevokedTokenRepository,
        time_provider: TimeGateway,
    ):
        self._user_password_repository = user_password_repository
        self._token_gateway = token_gateway
        self._sso_user_repository = sso_user_repository
        self._user_repository = user_repository
        self._revoked_token_repository = revoked_token_repository
        self._time_provider = time_provider

    def execute(self, command: ValidateUserTokenCommand) -> ValidateUserTokenResponse:
        token_obj = self._token_gateway.validate_token(command.jwt_token)
        if not token_obj:
            raise InvalidTokenException()

        now = self._time_provider.get_current_time()
        if token_obj.jti and self._revoked_token_repository.is_revoked(token_obj.jti, now):
            raise InvalidTokenException()

        authenticated_user = self._user_repository.get_by_id(token_obj.user_id)
        if authenticated_user is not None and authenticated_user.session_invalid_before is not None:
            session_cutoff = authenticated_user.session_invalid_before
            if token_obj.issued_at is None or token_obj.issued_at < session_cutoff:
                raise InvalidTokenException()

        # Run synchronous DB lookups in a thread pool to avoid blocking the event loop.
        # SQLAlchemy sessions are synchronous; calling them directly in an async context
        # blocks the uvicorn event loop and starves all other requests (including health probes).
        def _lookup_user():
            user_password = self._user_password_repository.get_by_id(token_obj.user_id)
            if user_password:
                return user_password.email, user_password.display_name
            sso_user = self._sso_user_repository.get_by_user_id(token_obj.user_id)
            if not sso_user:
                raise UserNotFoundException("User not found")
            return sso_user.email, sso_user.display_name

        email, display_name = _lookup_user()

        # Check required roles if specified
        if command.required_roles:
            if not token_obj.roles:
                raise InsufficientRoleException()
            if not set(command.required_roles).issubset(set(token_obj.roles)):
                raise InsufficientRoleException()

        return ValidateUserTokenResponse(
            is_valid=True,
            user_id=token_obj.user_id,
            email=email,
            display_name=display_name,
            roles=token_obj.roles if token_obj.roles else [],
        )

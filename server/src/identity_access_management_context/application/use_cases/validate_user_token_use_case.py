from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.gateways import (
    RevokedTokenRepository,
    TokenGateway,
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
        token_gateway: TokenGateway,
        user_repository: UserRepository,
        revoked_token_repository: RevokedTokenRepository,
        time_provider: TimeGateway,
    ):
        self._token_gateway = token_gateway
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
        if authenticated_user is None:
            raise UserNotFoundException("User not found")
        if authenticated_user.session_invalid_before is not None:
            session_cutoff = authenticated_user.session_invalid_before
            if token_obj.issued_at is None or token_obj.issued_at < session_cutoff:
                raise InvalidTokenException()

        # Check required roles if specified
        if command.required_roles:
            if not token_obj.roles:
                raise InsufficientRoleException()
            if not set(command.required_roles).issubset(set(token_obj.roles)):
                raise InsufficientRoleException()

        return ValidateUserTokenResponse(
            is_valid=True,
            user_id=token_obj.user_id,
            email=authenticated_user.email,
            display_name=authenticated_user.name,
            roles=token_obj.roles if token_obj.roles else [],
        )

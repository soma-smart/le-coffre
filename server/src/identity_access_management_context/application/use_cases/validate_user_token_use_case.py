from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.responses import (
    ValidateUserTokenResponse,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    TokenGateway,
    SessionRepository,
    SsoUserRepository,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    SessionNotFoundException,
    UserNotFoundException,
    InsufficientRoleException,
)


class ValidateUserTokenUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        token_gateway: TokenGateway,
        session_repository: SessionRepository,
        sso_user_repository: SsoUserRepository,
    ):
        self._user_password_repository = user_password_repository
        self._token_gateway = token_gateway
        self._session_repository = session_repository
        self._sso_user_repository = sso_user_repository

    async def execute(
        self, command: ValidateUserTokenCommand
    ) -> ValidateUserTokenResponse:
        token_obj = await self._token_gateway.validate_token(command.jwt_token)
        if not token_obj:
            raise InvalidTokenException()

        session = self._session_repository.get_by_token(command.jwt_token)
        if not session:
            raise SessionNotFoundException("Session not found or expired")

        # Try to find user in UserPassword repository (admin users)
        user_password = self._user_password_repository.get_by_id(session.user_id)
        if user_password:
            email = user_password.email
            display_name = user_password.display_name
        else:
            # Try to find user in SsoUser repository (SSO users)
            sso_user = self._sso_user_repository.get_by_email(token_obj.email)
            if not sso_user or sso_user.internal_user_id != session.user_id:
                raise UserNotFoundException("User not found")
            email = sso_user.email
            display_name = sso_user.display_name

        # Check required roles if specified
        if command.required_roles:
            if not token_obj.roles:
                raise InsufficientRoleException()
            if not set(command.required_roles).issubset(set(token_obj.roles)):
                raise InsufficientRoleException()

        return ValidateUserTokenResponse(
            is_valid=True,
            user_id=session.user_id,
            email=email,
            display_name=display_name,
            session_id=session.id,
            roles=token_obj.roles if token_obj.roles else [],
        )

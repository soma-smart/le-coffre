from identity_access_management_context.application.commands import (
    ValidateUserTokenCommand,
)
from identity_access_management_context.application.responses import (
    ValidateUserTokenResponse,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    TokenGateway,
    SsoUserRepository,
)
from identity_access_management_context.domain.exceptions import (
    InvalidTokenException,
    UserNotFoundException,
    InsufficientRoleException,
)


class ValidateUserTokenUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        token_gateway: TokenGateway,
        sso_user_repository: SsoUserRepository,
    ):
        self._user_password_repository = user_password_repository
        self._token_gateway = token_gateway
        self._sso_user_repository = sso_user_repository

    async def execute(
        self, command: ValidateUserTokenCommand
    ) -> ValidateUserTokenResponse:
        token_obj = await self._token_gateway.validate_token(command.jwt_token)
        if not token_obj:
            raise InvalidTokenException()

        # Try to find user in UserPassword repository (admin users)
        user_password = self._user_password_repository.get_by_id(token_obj.user_id)
        if user_password:
            email = user_password.email
            display_name = user_password.display_name
        else:
            # Try to find user in SsoUser repository (SSO users)
            sso_user = self._sso_user_repository.get_by_user_id(token_obj.user_id)
            if not sso_user:
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
            user_id=token_obj.user_id,
            email=email,
            display_name=display_name,
            roles=token_obj.roles if token_obj.roles else [],
        )

from authentication_context.application.commands import ValidateUserTokenCommand
from authentication_context.application.responses import ValidateUserTokenResponse
from authentication_context.application.gateways import (
    UserPasswordRepository,
    TokenGateway,
    SessionRepository,
)
from authentication_context.domain.exceptions import (
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
    ):
        self._user_password_repository = user_password_repository
        self._token_gateway = token_gateway
        self._session_repository = session_repository

    async def execute(
        self, command: ValidateUserTokenCommand
    ) -> ValidateUserTokenResponse:
        token_obj = await self._token_gateway.validate_token(command.jwt_token)
        if not token_obj:
            raise InvalidTokenException()

        session = self._session_repository.get_by_token(command.jwt_token)
        if not session:
            raise SessionNotFoundException("Session not found or expired")

        user_password = self._user_password_repository.get_by_id(session.user_id)
        if not user_password:
            raise UserNotFoundException("User not found")

        # Check required roles if specified
        if command.required_roles:
            if not token_obj.roles:
                raise InsufficientRoleException()
            if not set(command.required_roles).issubset(set(token_obj.roles)):
                raise InsufficientRoleException()

        return ValidateUserTokenResponse(
            is_valid=True,
            user_id=user_password.id,
            email=user_password.email,
            display_name=user_password.display_name,
            session_id=session.id,
        )

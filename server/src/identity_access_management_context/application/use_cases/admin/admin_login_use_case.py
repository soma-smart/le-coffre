from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.responses import AdminLoginResponse
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
    TokenGateway,
    SessionRepository,
)
from identity_access_management_context.domain.entities import AuthenticationSession
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)
from shared_kernel.authentication.constants import ADMIN_ROLE
from shared_kernel.time import TimeProvider


class AdminLoginUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        token_gateway: TokenGateway,
        session_repository: SessionRepository,
        time_provider: TimeProvider,
    ):
        self._user_password_repository = user_password_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._token_gateway = token_gateway
        self._session_repository = session_repository
        self._time_provider = time_provider

    async def execute(self, command: AdminLoginCommand) -> AdminLoginResponse:
        user_password = self._user_password_repository.get_by_email(command.email)
        if not user_password:
            raise AdminNotFoundException("User not found")

        if not self._password_hashing_gateway.verify(
            command.password, user_password.password_hash
        ):
            raise InvalidCredentialsException("Invalid credentials")

        token = await self._token_gateway.generate_token(
            user_id=user_password.id,
            email=user_password.email,
            roles=[ADMIN_ROLE],
            claims={"display_name": user_password.display_name},
        )

        session = AuthenticationSession(
            user_id=user_password.id,
            jwt_token=token.value,
            time_provider=self._time_provider,
        )
        self._session_repository.save(session)

        return AdminLoginResponse(
            jwt_token=token.value,
            admin_id=user_password.id,
            email=user_password.email,
        )

from authentication_context.application.commands import AdminLoginCommand
from authentication_context.application.responses import AdminLoginResponse
from authentication_context.application.gateways import (
    AdminRepository,
    PasswordHashingGateway,
    JWTTokenGateway,
    SessionRepository,
)
from authentication_context.domain.entities import AuthenticationSession
from authentication_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)


class AdminLoginUseCase:
    def __init__(
        self,
        admin_repository: AdminRepository,
        password_hashing_gateway: PasswordHashingGateway,
        jwt_token_gateway: JWTTokenGateway,
        session_repository: SessionRepository,
    ):
        self._admin_repository = admin_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._jwt_token_gateway = jwt_token_gateway
        self._session_repository = session_repository

    async def execute(self, command: AdminLoginCommand) -> AdminLoginResponse:
        admin = self._admin_repository.get_by_email(command.email)
        if not admin:
            raise AdminNotFoundException("Admin not found")

        if not self._password_hashing_gateway.verify_password(
            command.password, admin.password_hash
        ):
            raise InvalidCredentialsException("Invalid credentials")

        jwt_token = await self._jwt_token_gateway.generate_token(
            user_id=command.email,
            claims={"admin_id": str(admin.id), "email": admin.email},
        )

        session = AuthenticationSession(user_id=admin.id, jwt_token=jwt_token)
        self._session_repository.save(session)

        return AdminLoginResponse(
            jwt_token=jwt_token, admin_id=admin.id, email=admin.email
        )

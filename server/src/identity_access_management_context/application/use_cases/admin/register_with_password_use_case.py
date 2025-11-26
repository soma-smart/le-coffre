from uuid import UUID

from identity_access_management_context.application.commands import (
    RegisterWithPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
    UserManagementGateway,
)
from identity_access_management_context.domain.entities import UserPassword
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsException,
)


class RegisterWithPasswordUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        user_management_gateway: UserManagementGateway,
    ):
        self._user_password_repository = user_password_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._user_management_gateway = user_management_gateway

    async def execute(self, command: RegisterWithPasswordCommand) -> UUID:
        # Check if user with this email already exists
        existing_user = self._user_password_repository.get_by_email(command.email)
        if existing_user:
            raise UserAlreadyExistsException(command.email)

        password_hash = self._password_hashing_gateway.hash(command.password)

        user_password = UserPassword(
            id=command.id,
            email=command.email,
            password_hash=password_hash,
            display_name=command.display_name,
        )

        self._user_password_repository.save(user_password)

        # First user becomes admin, subsequent users are regular users
        can_create_admin = await self._user_management_gateway.can_create_admin()
        if can_create_admin:
            await self._user_management_gateway.create_admin(
                user_id=command.id,
                email=command.email,
                display_name=command.display_name,
            )
        else:
            await self._user_management_gateway.create_user(
                user_id=command.id,
                email=command.email,
                display_name=command.display_name,
            )

        return user_password.id

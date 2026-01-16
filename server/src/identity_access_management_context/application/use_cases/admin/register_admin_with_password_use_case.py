from uuid import UUID

from identity_access_management_context.application.commands import (
    RegisterAdminWithPasswordCommand,
    CreateUserCommand,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
)
from identity_access_management_context.application.use_cases import (
    CreateAdminUseCase,
    CanCreateAdminUseCase,
)
from identity_access_management_context.domain.entities import UserPassword
from identity_access_management_context.domain.exceptions import (
    AdminAlreadyExistsException,
)


class RegisterAdminWithPasswordUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        create_admin_usecase: CreateAdminUseCase,
        can_create_admin_usecase: CanCreateAdminUseCase,
    ):
        self._user_password_repository = user_password_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._create_admin_usecase = create_admin_usecase
        self._can_create_admin_usecase = can_create_admin_usecase

    async def execute(self, command: RegisterAdminWithPasswordCommand) -> UUID:
        can_create_response = self._can_create_admin_usecase.execute()
        if not can_create_response.can_create:
            raise AdminAlreadyExistsException("An admin account already exists")

        password_hash = self._password_hashing_gateway.hash(command.password)

        user_password = UserPassword(
            id=command.id,
            email=command.email,
            password_hash=password_hash,
            display_name=command.display_name,
        )

        self._user_password_repository.save(user_password)

        create_user_command = CreateUserCommand(
            id=command.id,
            email=command.email,
            username=command.email.split("@")[0],
            name=command.display_name,
        )
        self._create_admin_usecase.execute(create_user_command)

        return user_password.id

from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
)
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    InvalidCredentialsException,
)


class UpdateUserPasswordUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
    ):
        self.user_password_repository = user_password_repository
        self.password_hashing_gateway = password_hashing_gateway

    def execute(self, command: UpdateUserPasswordCommand) -> None:
        user_password = self.user_password_repository.get_by_id(command.user_id)
        if not user_password:
            raise UserNotFoundException(command.user_id)

        if not self.password_hashing_gateway.verify(
            command.old_password, user_password.password_hash
        ):
            raise InvalidCredentialsException("Invalid old password")

        new_password_hash = self.password_hashing_gateway.hash(command.new_password)
        user_password.password_hash = new_password_hash

        self.user_password_repository.update(user_password)

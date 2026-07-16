from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
    UserPasswordRepository,
)
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import RawPassword
from shared_kernel.application.tracing import TracedUseCase


class UpdateUserPasswordUseCase(TracedUseCase):
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

        if not self.password_hashing_gateway.verify(command.old_password, user_password.password_hash):
            raise InvalidCredentialsException("Invalid old password")

        # Checked after the old password so a wrong current password still answers 401
        # rather than leaking policy feedback first.
        new_password = RawPassword(command.new_password)

        new_password_hash = self.password_hashing_gateway.hash(new_password.value)

        self.user_password_repository.update_password(command.user_id, new_password_hash)

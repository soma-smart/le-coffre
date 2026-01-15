from password_management_context.application.commands import UnshareResourceCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    CannotUnshareWithOwnerError,
    PasswordNotFoundError,
)


class UnshareAccessUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository

    def execute(self, command: UnshareResourceCommand):
        if not self.password_permissions_repository.is_owner(
            command.owner_id, command.password_id
        ):
            raise PasswordAccessDeniedError(command.owner_id, command.password_id)

        if not self.password_repository.get_by_id(command.password_id):
            raise PasswordNotFoundError(command.password_id)

        if self.password_permissions_repository.is_owner(
            command.user_id, command.password_id
        ):
            raise CannotUnshareWithOwnerError(command.user_id, command.password_id)

        self.password_permissions_repository.revoke_access(
            command.user_id, command.password_id
        )

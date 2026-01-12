from password_management_context.application.commands import ShareResourceCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
)
from password_management_context.domain.value_objects import PasswordPermission


class ShareAccessUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository

    def execute(self, command: ShareResourceCommand):
        # Verify the password exists - will raise PasswordNotFoundError if not
        self.password_repository.get_by_id(command.password_id)

        # Check if requester is the owner
        if not self.password_permissions_repository.is_owner(
            command.owner_id, command.password_id
        ):
            raise PasswordAccessDeniedError(command.owner_id, command.password_id)

        if not self.password_repository.get_by_id(command.password_id):
            raise PasswordNotFoundError(command.password_id)

        self.password_permissions_repository.grant_access(
            command.user_id, command.password_id, PasswordPermission.READ
        )

from password_management_context.application.commands import IsGroupUsedCommand
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)


from shared_kernel.application.tracing import TracedUseCase


class IsGroupUsedUseCase(TracedUseCase):
    def __init__(self, password_permissions_repository: PasswordPermissionsRepository):
        self.password_permissions_repository = password_permissions_repository

    def execute(self, command: IsGroupUsedCommand) -> bool:
        return self.password_permissions_repository.has_any_password_for_group(
            command.group_id
        )

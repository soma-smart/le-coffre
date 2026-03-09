from password_management_context.application.commands import CheckAccessCommand
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from shared_kernel.application.metrics import access_check_not_found_counter
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.value_objects import AccessResult, Granted


class CheckAccessUseCase(TracedUseCase):
    def __init__(self, permission_repository: PasswordPermissionsRepository):
        self.permission_repository = permission_repository

    def execute(self, command: CheckAccessCommand) -> AccessResult:
        if self.permission_repository.is_owner(command.user_id, command.resource_id):
            return AccessResult(granted=Granted.ACCESS, is_owner=True)

        has_permission = self.permission_repository.has_access(command.user_id, command.resource_id, command.permission)

        if not has_permission:
            access_check_not_found_counter.add(1)
            return AccessResult(granted=Granted.NOT_FOUND)

        return AccessResult(granted=Granted.ACCESS)

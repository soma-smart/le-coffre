from password_management_context.application.commands import CheckAccessCommand
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.metrics import access_check_not_found_counter
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.value_objects import AccessResult, Granted


class CheckAccessUseCase(TracedUseCase):
    def __init__(self, permission_repository: PasswordPermissionsRepository, time_gateway: TimeGateway):
        self.permission_repository = permission_repository
        self.time_gateway = time_gateway

    def execute(self, command: CheckAccessCommand) -> AccessResult:
        # The decision goes through PasswordGroupAccess so a lapsed share is
        # refused here exactly as it is when the password is read.
        access = self.permission_repository.list_all_permissions_for(command.resource_id).get(command.user_id)

        if access is not None and access.is_owner:
            return AccessResult(granted=Granted.ACCESS, is_owner=True)

        if access is None or not access.grants_read(self.time_gateway.get_current_time()):
            access_check_not_found_counter.add(1)
            return AccessResult(granted=Granted.NOT_FOUND)

        return AccessResult(granted=Granted.ACCESS)

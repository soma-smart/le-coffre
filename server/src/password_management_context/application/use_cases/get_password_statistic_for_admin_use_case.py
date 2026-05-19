from password_management_context.application.commands import GetPasswordStatisticForAdminCommand
from password_management_context.application.gateways import PasswordRepository
from password_management_context.application.responses import GetPasswordStatisticForAdminResponse
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class GetPasswordStatisticForAdminUseCase(TracedUseCase):
    def __init__(self, password_repository: PasswordRepository):
        self.password_repository = password_repository

    def execute(self, command: GetPasswordStatisticForAdminCommand) -> GetPasswordStatisticForAdminResponse:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "get password statistics")

        return GetPasswordStatisticForAdminResponse(
            password_count=self.password_repository.count(),
        )

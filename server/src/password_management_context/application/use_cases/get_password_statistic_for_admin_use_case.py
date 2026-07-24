from password_management_context.application.commands import GetPasswordStatisticForAdminCommand
from password_management_context.application.gateways import OneTimeLinkRepository, PasswordRepository
from password_management_context.application.responses import GetPasswordStatisticForAdminResponse
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class GetPasswordStatisticForAdminUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        one_time_link_repository: OneTimeLinkRepository,
        time_gateway: TimeGateway,
    ):
        self.password_repository = password_repository
        self.one_time_link_repository = one_time_link_repository
        self.time_gateway = time_gateway

    def execute(self, command: GetPasswordStatisticForAdminCommand) -> GetPasswordStatisticForAdminResponse:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "get password statistics")

        return GetPasswordStatisticForAdminResponse(
            password_count=self.password_repository.count(),
            # Two numbers rather than one: the total measures usage over time,
            # while the active count is the only one that says how many anonymous
            # read grants are open on the vault right now.
            one_time_link_count=self.one_time_link_repository.count_all(),
            active_one_time_link_count=self.one_time_link_repository.count_active_all(
                self.time_gateway.get_current_time()
            ),
        )

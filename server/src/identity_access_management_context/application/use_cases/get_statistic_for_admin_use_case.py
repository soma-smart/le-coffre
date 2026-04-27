from identity_access_management_context.application.commands import GetStatisticForAdminCommand
from identity_access_management_context.application.gateways import GroupRepository, UserRepository
from identity_access_management_context.application.responses import GetStatisticForAdminResponse
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services.admin_permission_checker import AdminPermissionChecker


class GetStatisticForAdminUseCase(TracedUseCase):
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository

    def execute(self, command: GetStatisticForAdminCommand) -> GetStatisticForAdminResponse:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "get statistics")

        return GetStatisticForAdminResponse(
            user_count=self.user_repository.count(),
            group_count=self.group_repository.count_non_personal(),
        )

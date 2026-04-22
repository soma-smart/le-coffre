from identity_access_management_context.application.commands import GetAdminStatCommand
from identity_access_management_context.application.gateways import (
    GroupRepository,
    UserPasswordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses.admin_stat_responce import (
    AdminStatResponse,
)
from shared_kernel.application.tracing import TracedUseCase


class GetAdminStatUseCase(TracedUseCase):
    def __init__(
        self,
        GroupRepository: GroupRepository,
        UserRepository: UserRepository,
        UserPasswordRepository: UserPasswordRepository,
    ):
        self.group_repository = GroupRepository
        self.user_repository = UserRepository
        self.password_repository = UserPasswordRepository

    def execute(self, command: GetAdminStatCommand) -> AdminStatResponse:
        number_of_users = self.user_repository.count()
        number_of_groups = self.group_repository.get_number_of_groups_not_personal()
        number_of_passwords = self.password_repository.count()

        return AdminStatResponse(
            groupCount=number_of_groups,
            userCount=number_of_users,
            passwordCount=number_of_passwords,
        )

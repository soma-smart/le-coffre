from identity_access_management_context.application.commands import ListUserCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class ListUserUseCase(TracedUseCase):
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: ListUserCommand) -> list[User]:
        AdminPermissionChecker().ensure_admin(command.requesting_user, "list users")
        return self.user_repository.list_all()

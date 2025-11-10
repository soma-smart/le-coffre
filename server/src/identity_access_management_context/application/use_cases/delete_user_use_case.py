from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.commands import DeleteUserCommand
from shared_kernel.domain import AdminPermissionService


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: DeleteUserCommand) -> None:
        AdminPermissionService.ensure_admin(command.requesting_user, "delete users")
        user_id = command.user_id

        self.user_repository.delete(user_id)

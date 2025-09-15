from user_management_context.application.interfaces import UserRepository
from user_management_context.application.commands import DeleteUserCommand
from shared_kernel.authentication import AdminPermissionChecker


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: DeleteUserCommand) -> None:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "delete users")
        user_id = command.user_id

        self.user_repository.delete(user_id)

from identity_access_management_context.application.commands import PromoteAdminCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.exceptions import UserNotFoundException
from shared_kernel.domain.services import AdminPermissionChecker


class PromoteAdminUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: PromoteAdminCommand) -> None:
        AdminPermissionChecker.ensure_admin(
            command.requesting_user, "promote users to admin"
        )

        user = self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        user.promote_to_admin()
        self.user_repository.update(user)

from uuid import UUID
from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.exceptions import PasswordNotFoundError
from shared_kernel.access_control import Granted, AccessController, AccessDeniedError


class DeletePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        access_controller: AccessController,
    ):
        self.password_repository = password_repository
        self.access_controller = access_controller

    def execute(self, requester_id: UUID, password_id: UUID) -> None:
        if not self.password_repository.get_by_id(password_id):
            raise PasswordNotFoundError(password_id)
        check_permission = self.access_controller.check_delete_access(
            requester_id, password_id
        )
        if check_permission.granted == Granted.VIEW_ONLY:
            raise AccessDeniedError(requester_id, password_id)
        if check_permission.granted == Granted.NOT_FOUND:
            raise PasswordNotFoundError(password_id)
        self.password_repository.delete(password_id)

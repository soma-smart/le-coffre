from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.exceptions import PasswordNotFoundError
from shared_kernel.access_control import Granted, AccessController, AccessDeniedError
from shared_kernel.encryption import EncryptionService


class UpdatePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        access_controller: AccessController,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.access_controller = access_controller

    def execute(self, new_password: UpdatePasswordCommand) -> None:
        if not self.password_repository.get_by_id(new_password.id):
            raise PasswordNotFoundError(new_password.id)
        check_permission = self.access_controller.check_update_access(
            new_password.requester_id, new_password.id
        )
        if check_permission.granted == Granted.VIEW_ONLY:
            raise AccessDeniedError(new_password.requester_id, new_password.id)
        if check_permission.granted == Granted.NOT_FOUND:
            raise PasswordNotFoundError(new_password.id)

        existing_password = self.password_repository.get_by_id(new_password.id)

        if new_password.password:
            existing_password.encrypted_value = self.encryption_service.encrypt(new_password.password)

        if new_password.name:
            existing_password.name = new_password.name

        if new_password.folder:
            existing_password.folder = new_password.folder

        self.password_repository.update(existing_password)

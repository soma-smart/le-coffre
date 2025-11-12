from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.exceptions import PasswordNotFoundError
from shared_kernel.application.gateways import (
    EncryptionGateway,
    AccessController,
    Granted,
)
from shared_kernel.domain.exceptions import AccessDeniedError


class UpdatePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_gateway: EncryptionGateway,
        access_controller: AccessController,
    ):
        self.password_repository = password_repository
        self.encryption_gateway = encryption_gateway
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

        encrypted_value = self.encryption_gateway.encrypt(new_password.password)

        updated_password = Password(
            id=new_password.id,
            name=new_password.name,
            encrypted_value=encrypted_value,
            folder=new_password.folder,
        )

        self.password_repository.update(updated_password)

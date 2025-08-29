from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.services import PasswordAccessService
from shared_kernel.encryption import EncryptionService
from shared_kernel.access_control import AccessController


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
        PasswordAccessService.ensure_access(
            self.access_controller, new_password.requester_id, new_password.id
        )

        encrypted_value = self.encryption_service.encrypt(new_password.password)

        updated_password = Password.create(
            id=new_password.id,
            name=new_password.name,
            encrypted_value=encrypted_value,
            folder=new_password.folder,
        )

        self.password_repository.update(updated_password)

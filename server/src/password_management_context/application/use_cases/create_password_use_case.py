from uuid import UUID

from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.domain.services.password_complexity_service import (
    PasswordComplexityService,
)
from shared_kernel.encryption import EncryptionService
from shared_kernel.access_control import AccessController


class CreatePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        access_controller: AccessController,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.access_controller = access_controller

    def execute(self, command: CreatePasswordCommand) -> UUID:
        PasswordComplexityService.validate(command.decrypted_password)

        encrypted_value = self.encryption_service.encrypt(command.decrypted_password)

        password = Password.create(
            id=command.id,
            name=command.name,
            encrypted_value=encrypted_value,
            folder=command.folder,
        )

        self.password_repository.save(password)
        self.access_controller.set_owner(command.user_id, password.id)

        return password.id

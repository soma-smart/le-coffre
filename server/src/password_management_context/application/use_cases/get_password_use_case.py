from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.application.responses import PasswordResponse
from password_management_context.domain.services import PasswordAccessService
from shared_kernel.encryption import EncryptionService
from shared_kernel.access_control import AccessController


class GetPasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        access_controller: AccessController,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.access_controller = access_controller

    def execute(self, user_id: UUID, password_id: UUID) -> PasswordResponse:
        password_entity = self.password_repository.get_by_id(password_id)

        authorized_password = PasswordAccessService.ensure_access_and_get_password(
            self.access_controller, user_id, password_entity
        )

        decrypted_password = self.encryption_service.decrypt(
            authorized_password.encrypted_value
        )

        return PasswordResponse(
            id=authorized_password.id,
            name=authorized_password.name,
            password=decrypted_password,
            folder=authorized_password.folder,
        )

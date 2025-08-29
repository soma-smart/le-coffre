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

    def execute(self, requester_id: UUID, password_id: UUID) -> PasswordResponse:
        PasswordAccessService.ensure_access(
            self.access_controller, requester_id, password_id
        )

        password_entity = self.password_repository.get_by_id(password_id)

        decrypted_password = self.encryption_service.decrypt(
            password_entity.encrypted_value
        )

        return PasswordResponse(
            id=password_entity.id,
            name=password_entity.name,
            password=decrypted_password,
            folder=password_entity.folder,
        )

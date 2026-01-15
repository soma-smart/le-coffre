from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.application.responses import PasswordResponse
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from shared_kernel.encryption import EncryptionService


class GetPasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        password_permissions_repository: PasswordPermissionsRepository,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.password_permissions_repository = password_permissions_repository

    def execute(self, requester_id: UUID, password_id: UUID) -> PasswordResponse:
        password_entity = self.password_repository.get_by_id(password_id)
        if not password_entity:
            raise PasswordNotFoundError(password_id)

        if not self.password_permissions_repository.has_access(
            requester_id, password_id
        ):
            raise PasswordAccessDeniedError(requester_id, password_id)

        decrypted_password = self.encryption_service.decrypt(
            password_entity.encrypted_value
        )

        return PasswordResponse(
            id=password_entity.id,
            name=password_entity.name,
            password=decrypted_password,
            folder=password_entity.folder,
        )

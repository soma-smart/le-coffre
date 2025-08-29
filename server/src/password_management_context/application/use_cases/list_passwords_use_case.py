from typing import List, Optional

from password_management_context.application.gateways import PasswordRepository
from password_management_context.application.responses import PasswordResponse
from password_management_context.domain.exceptions import FolderNotFoundError
from shared_kernel.encryption import EncryptionService


class ListPasswordsUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service

    def execute(self, folder: Optional[str] = None) -> List[PasswordResponse]:
        password_entities = self.password_repository.list_all(folder)

        if folder and len(password_entities) == 0:
            raise FolderNotFoundError(folder)
        password_responses = []
        for password_entity in password_entities:
            decrypted_password = self.encryption_service.decrypt(
                password_entity.encrypted_value
            )

            password_response = PasswordResponse(
                id=password_entity.id,
                name=password_entity.name,
                password=decrypted_password,
                folder=password_entity.folder,
            )
            password_responses.append(password_response)

        return password_responses

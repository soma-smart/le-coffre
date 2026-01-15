from typing import List, Optional
from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.application.responses import PasswordMetadataResponse
from password_management_context.domain.exceptions import FolderNotFoundError


class ListPasswordsUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository

    def execute(
        self, requester_id: UUID, folder: Optional[str] = None
    ) -> List[PasswordMetadataResponse]:
        password_entities = self.password_repository.list_all(folder)

        if folder and len(password_entities) == 0:
            raise FolderNotFoundError(folder)

        password_responses = []
        for password_entity in password_entities:
            if self.password_permissions_repository.has_access(
                requester_id, password_entity.id
            ):
                password_response = PasswordMetadataResponse(
                    id=password_entity.id,
                    name=password_entity.name,
                    folder=password_entity.folder,
                )
                password_responses.append(password_response)

        return password_responses

from typing import List, Optional
from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.application.responses import PasswordMetadataResponse
from password_management_context.domain.exceptions import FolderNotFoundError
from shared_kernel.access_control import Granted, AccessController


class ListPasswordsUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        access_controller: AccessController,
    ):
        self.password_repository = password_repository
        self.access_controller = access_controller

    def execute(
        self, requester_id: UUID, folder: Optional[str] = None
    ) -> List[PasswordMetadataResponse]:
        password_entities = self.password_repository.list_all(folder)

        if folder and len(password_entities) == 0:
            raise FolderNotFoundError(folder)

        password_responses = []
        for password_entity in password_entities:
            check_permission = self.access_controller.check_access(
                requester_id, password_entity.id
            )
            if check_permission.granted in (Granted.ACCESS, Granted.VIEW_ONLY):
                password_response = PasswordMetadataResponse(
                    id=password_entity.id,
                    name=password_entity.name,
                    folder=password_entity.folder,
                )
                password_responses.append(password_response)

        return password_responses

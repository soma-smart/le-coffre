from typing import List, Optional
from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.application.responses import PasswordMetadataResponse
from password_management_context.domain.exceptions import FolderNotFoundError
from password_management_context.domain.value_objects import PasswordPermission


class ListPasswordsUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway

    def execute(
        self, requester_id: UUID, folder: Optional[str] = None
    ) -> List[PasswordMetadataResponse]:
        password_entities = self.password_repository.list_all(folder)

        if folder and len(password_entities) == 0:
            raise FolderNotFoundError(folder)

        password_responses = []
        for password_entity in password_entities:
            if self._user_has_access_through_groups(requester_id, password_entity.id):
                password_response = PasswordMetadataResponse(
                    id=password_entity.id,
                    name=password_entity.name,
                    folder=password_entity.folder,
                )
                password_responses.append(password_response)

        return password_responses

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user owns this group
            if self.group_access_gateway.is_user_owner_of_group(user_id, group_id):
                # If the group is the owner or has READ permission, user has access
                if is_owner or PasswordPermission.READ in permissions:
                    return True

        return False

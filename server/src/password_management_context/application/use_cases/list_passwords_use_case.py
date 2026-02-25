from typing import List, Optional
from uuid import UUID

from password_management_context.application.commands import ListPasswordsCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
    PasswordEventRepository,
)
from password_management_context.application.responses import PasswordMetadataResponse
from password_management_context.application.services import PasswordTimestampService
from password_management_context.domain.exceptions import FolderNotFoundError
from password_management_context.domain.value_objects import PasswordPermission


from shared_kernel.application.tracing import TracedUseCase


class ListPasswordsUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        password_event_repository: PasswordEventRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.password_event_repository = password_event_repository

    def execute(self, command: ListPasswordsCommand) -> List[PasswordMetadataResponse]:
        password_entities = self.password_repository.list_all(command.folder)

        if command.folder and len(password_entities) == 0:
            raise FolderNotFoundError(command.folder)

        password_responses = []
        accessible_passwords = []

        for password_entity in password_entities:
            access_info = self._user_has_access_through_groups(
                command.requester_id, password_entity.id
            )
            if access_info is not None:
                user_group_id, owner_group_id = access_info
                accessible_passwords.append((password_entity, owner_group_id))

        if not accessible_passwords:
            return []

        timestamp_service = PasswordTimestampService(self.password_event_repository)
        password_ids = [pwd.id for pwd, _ in accessible_passwords]
        timestamps_map = timestamp_service.get_timestamps_bulk(password_ids)

        for password_entity, owner_group_id in accessible_passwords:
            created_at, last_password_updated_at = timestamps_map.get(
                password_entity.id, (None, None)
            )
            password_response = PasswordMetadataResponse(
                id=password_entity.id,
                name=password_entity.name,
                folder=password_entity.folder,
                group_id=owner_group_id,
                created_at=created_at,
                last_password_updated_at=last_password_updated_at,
            )
            password_responses.append(password_response)

        return password_responses

    def _user_has_access_through_groups(
        self, user_id: UUID, password_id: UUID
    ) -> Optional[tuple[UUID, UUID]]:
        """Check if user has access to password through any of their groups.

        Returns a tuple of (user_group_id, owner_group_id) if access is granted, None otherwise.
        - user_group_id: The group through which the user has access
        - owner_group_id: The group that owns the password
        """
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        # Find the owner group first
        owner_group_id = None
        for group_id, (is_owner, permissions) in all_permissions.items():
            if is_owner:
                owner_group_id = group_id
                break

        if owner_group_id is None:
            return None  # No owner found, something is wrong

        # Check if user has access through any of their groups
        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user is owner or member of this group
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                # If the group is the owner or has READ permission, user has access
                if is_owner or PasswordPermission.READ in permissions:
                    return (group_id, owner_group_id)

        return None

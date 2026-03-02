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
from shared_kernel.domain.services import AdminPermissionChecker


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

    def execute(self, command: ListPasswordsCommand) -> list[PasswordMetadataResponse]:
        password_entities = self.password_repository.list_all(command.folder)

        if command.folder and len(password_entities) == 0:
            raise FolderNotFoundError(command.folder)

        if AdminPermissionChecker.is_admin(command.requester):
            return self._build_admin_responses(password_entities)

        accessible_passwords = []

        for password_entity in password_entities:
            access_info = self._user_has_access_through_groups(
                command.requester.user_id, password_entity.id
            )
            if access_info is not None:
                user_group_id, owner_group_id, is_owner_access = access_info
                accessible_passwords.append(
                    (password_entity, owner_group_id, is_owner_access)
                )

        if not accessible_passwords:
            return []

        timestamp_service = PasswordTimestampService(self.password_event_repository)
        password_ids = [pwd.id for pwd, _, __ in accessible_passwords]
        timestamps_map = timestamp_service.get_timestamps_bulk(password_ids)

        password_responses = []
        for password_entity, owner_group_id, is_owner_access in accessible_passwords:
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
                can_read=True,
                can_write=is_owner_access,
            )
            password_responses.append(password_response)

        return password_responses

    def _build_admin_responses(
        self, password_entities
    ) -> List[PasswordMetadataResponse]:
        accessible_passwords = []
        for password_entity in password_entities:
            owner_group_id = self._find_owner_group_id(password_entity.id)
            if owner_group_id is not None:
                accessible_passwords.append((password_entity, owner_group_id))

        if not accessible_passwords:
            return []

        timestamp_service = PasswordTimestampService(self.password_event_repository)
        password_ids = [pwd.id for pwd, _ in accessible_passwords]
        timestamps_map = timestamp_service.get_timestamps_bulk(password_ids)

        password_responses = []
        for password_entity, owner_group_id in accessible_passwords:
            created_at, last_password_updated_at = timestamps_map.get(
                password_entity.id, (None, None)
            )
            password_responses.append(
                PasswordMetadataResponse(
                    id=password_entity.id,
                    name=password_entity.name,
                    folder=password_entity.folder,
                    group_id=owner_group_id,
                    created_at=created_at,
                    last_password_updated_at=last_password_updated_at,
                    can_read=False,
                    can_write=False,
                )
            )
        return password_responses

    def _find_owner_group_id(self, password_id: UUID) -> Optional[UUID]:
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )
        for group_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                return group_id
        return None

    def _user_has_access_through_groups(
        self, user_id: UUID, password_id: UUID
    ) -> tuple[UUID, UUID, bool] | None:
        """Check if user has access to password through any of their groups.

        Returns a tuple of (user_group_id, owner_group_id, is_owner_access) if access is granted, None otherwise.
        - user_group_id: The group through which the user has access
        - owner_group_id: The group that owns the password
        - is_owner_access: True if the user's group owns the password (full write access)
        """
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        owner_group_id = None
        for group_id, (is_owner, permissions) in all_permissions.items():
            if is_owner:
                owner_group_id = group_id
                break

        if owner_group_id is None:
            return None

        for group_id, (is_owner, permissions) in all_permissions.items():
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                if is_owner:
                    return (group_id, owner_group_id, True)
                elif PasswordPermission.READ in permissions:
                    return (group_id, owner_group_id, False)

        return None

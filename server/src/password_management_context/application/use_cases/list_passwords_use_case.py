from uuid import UUID

from password_management_context.application.commands import ListPasswordsCommand
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordEventRepository,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.gateways.password_permissions_repository import (
    BulkGroupPermissions,
    GroupPermissions,
)
from password_management_context.application.responses import PasswordMetadataResponse
from password_management_context.application.services import PasswordTimestampService
from password_management_context.domain.exceptions import FolderNotFoundError
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


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

        if not password_entities:
            return []

        password_ids = [p.id for p in password_entities]
        all_permissions = self.password_permissions_repository.list_all_permissions_for_bulk(password_ids)

        is_admin = AdminPermissionChecker.is_admin(command.requester)
        accessible = self._resolve_access(command.requester.user_id, password_entities, all_permissions, is_admin)

        if not accessible:
            return []

        timestamps_map = PasswordTimestampService(self.password_event_repository).get_timestamps_bulk(
            [p.id for p, *_ in accessible]
        )

        return [
            PasswordMetadataResponse(
                id=password.id,
                name=password.name,
                folder=password.folder,
                group_id=owner_group_id,
                created_at=timestamps_map.get(password.id, (None, None))[0],
                last_password_updated_at=timestamps_map.get(password.id, (None, None))[1],
                can_read=can_read,
                can_write=can_write,
            )
            for password, owner_group_id, can_read, can_write in accessible
        ]

    def _resolve_access(
        self,
        user_id: UUID,
        password_entities,
        all_permissions: BulkGroupPermissions,
        is_admin: bool,
    ) -> list[tuple]:
        membership_cache: dict[UUID, tuple[bool, bool]] = {}
        result = []

        for password in password_entities:
            permissions = all_permissions.get(password.id, {})
            owner_group_id = next((gid for gid, (is_owner, _) in permissions.items() if is_owner), None)
            if owner_group_id is None:
                continue

            user_access = self._find_user_access(user_id, permissions, membership_cache)

            if user_access is not None:
                can_write = user_access
                result.append((password, owner_group_id, True, can_write))
            elif is_admin:
                result.append((password, owner_group_id, False, False))

        return result

    def _find_user_access(
        self,
        user_id: UUID,
        permissions: GroupPermissions,
        membership_cache: dict[UUID, tuple[bool, bool]],
    ) -> bool | None:
        """Return True if the user has write access, False for read-only, None if no access."""
        for group_id, (is_owner_group, perms) in permissions.items():
            is_user_owner, is_user_member = self._cached_membership(user_id, group_id, membership_cache)
            if is_user_owner or is_user_member:
                if is_owner_group:
                    return True
                if PasswordPermission.READ in perms:
                    return False
        return None

    def _cached_membership(
        self,
        user_id: UUID,
        group_id: UUID,
        cache: dict[UUID, tuple[bool, bool]],
    ) -> tuple[bool, bool]:
        if group_id not in cache:
            cache[group_id] = (
                self.group_access_gateway.is_user_owner_of_group(user_id, group_id),
                self.group_access_gateway.is_user_member_of_group(user_id, group_id),
            )
        return cache[group_id]

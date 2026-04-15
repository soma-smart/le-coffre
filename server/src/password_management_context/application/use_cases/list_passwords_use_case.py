from dataclasses import dataclass
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
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import FolderNotFoundError
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker

TimestampsMap = dict[UUID, tuple]
MembershipCache = dict[UUID, tuple[bool, bool]]


@dataclass
class _PasswordAccessEntry:
    password: Password
    owner_group_id: UUID
    can_read: bool
    can_write: bool
    visible_group_ids: list[UUID]


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
        passwords = self._fetch_passwords(command.folder)
        if not passwords:
            return []

        permissions = self._fetch_permissions(passwords)
        entries = self._build_access_entries(command, passwords, permissions)
        if not entries:
            return []

        timestamps = self._fetch_timestamps(entries)
        return [self._to_response(entry, timestamps) for entry in entries]

    def _fetch_passwords(self, folder: str | None) -> list[Password]:
        passwords = self.password_repository.list_all(folder)
        if folder and not passwords:
            raise FolderNotFoundError(folder)
        return passwords

    def _fetch_permissions(self, passwords: list[Password]) -> BulkGroupPermissions:
        return self.password_permissions_repository.list_all_permissions_for_bulk([p.id for p in passwords])

    def _fetch_timestamps(self, entries: list[_PasswordAccessEntry]) -> TimestampsMap:
        return PasswordTimestampService(self.password_event_repository).get_timestamps_bulk(
            [e.password.id for e in entries]
        )

    def _build_access_entries(
        self,
        command: ListPasswordsCommand,
        passwords: list[Password],
        all_permissions: BulkGroupPermissions,
    ) -> list[_PasswordAccessEntry]:
        is_admin = AdminPermissionChecker.is_admin(command.requester)
        cache: MembershipCache = {}
        entries = []
        for password in passwords:
            entry = self._access_entry_for(command.requester.user_id, password, all_permissions, is_admin, cache)
            if entry is not None:
                entries.append(entry)
        return entries

    def _access_entry_for(
        self,
        user_id: UUID,
        password: Password,
        all_permissions: BulkGroupPermissions,
        is_admin: bool,
        cache: MembershipCache,
    ) -> _PasswordAccessEntry | None:
        permissions = all_permissions.get(password.id, {})
        owner_group_id = self._find_owner_group_id(permissions)
        if owner_group_id is None:
            return None

        all_group_ids = list(permissions.keys())
        user_access = self._find_user_access(user_id, permissions, cache)

        if user_access is not None:
            visible_ids = self._visible_group_ids_for_user(user_id, owner_group_id, all_group_ids, cache)
            return _PasswordAccessEntry(
                password, owner_group_id, can_read=True, can_write=user_access, visible_group_ids=visible_ids
            )

        if is_admin:
            # Admins should know everything
            return _PasswordAccessEntry(
                password, owner_group_id, can_read=False, can_write=False, visible_group_ids=all_group_ids
            )

        return None

    def _to_response(self, entry: _PasswordAccessEntry, timestamps: TimestampsMap) -> PasswordMetadataResponse:
        created_at, last_updated_at = timestamps.get(entry.password.id, (None, None))
        return PasswordMetadataResponse(
            id=entry.password.id,
            name=entry.password.name,
            folder=entry.password.folder,
            group_id=entry.owner_group_id,
            created_at=created_at,
            last_password_updated_at=last_updated_at,
            can_read=entry.can_read,
            can_write=entry.can_write,
            login=entry.password.login,
            url=entry.password.url,
            accessible_group_ids=tuple(entry.visible_group_ids),
        )

    def _find_owner_group_id(self, permissions: GroupPermissions) -> UUID | None:
        return next((gid for gid, (is_owner, _) in permissions.items() if is_owner), None)

    def _visible_group_ids_for_user(
        self,
        user_id: UUID,
        owner_group_id: UUID,
        all_group_ids: list[UUID],
        cache: MembershipCache,
    ) -> list[UUID]:
        if self._user_belongs_to_group(user_id, owner_group_id, cache):
            return all_group_ids
        return [
            gid for gid in all_group_ids if gid == owner_group_id or self._user_belongs_to_group(user_id, gid, cache)
        ]

    def _find_user_access(
        self,
        user_id: UUID,
        permissions: GroupPermissions,
        cache: MembershipCache,
    ) -> bool | None:
        for group_id, (is_owner_group, perms) in permissions.items():
            if self._user_belongs_to_group(user_id, group_id, cache):
                if is_owner_group:
                    return True
                if PasswordPermission.READ in perms:
                    return False
        return None

    def _user_belongs_to_group(self, user_id: UUID, group_id: UUID, cache: MembershipCache) -> bool:
        is_owner, is_member = self._cached_membership(user_id, group_id, cache)
        return is_owner or is_member

    def _cached_membership(self, user_id: UUID, group_id: UUID, cache: MembershipCache) -> tuple[bool, bool]:
        if group_id not in cache:
            cache[group_id] = (
                self.group_access_gateway.is_user_owner_of_group(user_id, group_id),
                self.group_access_gateway.is_user_member_of_group(user_id, group_id),
            )
        return cache[group_id]

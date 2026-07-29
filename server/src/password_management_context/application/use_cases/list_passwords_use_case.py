from dataclasses import dataclass
from datetime import datetime
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
from shared_kernel.application.gateways.time_gateway import TimeGateway
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
    access_expires_at: datetime | None = None


@dataclass
class _UserAccess:
    """How the requester reaches one password, and until when.

    can_write is the owning-group membership; access_expires_at is the deadline
    of the share the user came through, so the UI can warn them before it lapses.
    """

    can_write: bool
    expires_at: datetime | None


class ListPasswordsUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        password_event_repository: PasswordEventRepository,
        time_gateway: TimeGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.password_event_repository = password_event_repository
        self.time_gateway = time_gateway

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
        now = self.time_gateway.get_current_time()
        cache: MembershipCache = {}
        entries = []
        for password in passwords:
            entry = self._access_entry_for(command.requester.user_id, password, all_permissions, is_admin, cache, now)
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
        now: datetime,
    ) -> _PasswordAccessEntry | None:
        permissions = all_permissions.get(password.id, {})
        owner_group_id = self._find_owner_group_id(permissions)
        if owner_group_id is None:
            return None

        # An expired share is dropped here rather than filtered downstream, so it
        # can neither grant the password nor show up as a group it reaches.
        all_group_ids = [gid for gid, access in permissions.items() if access.is_active(now)]
        user_access = self._find_user_access(user_id, permissions, cache, now)

        if user_access is not None:
            visible_ids = self._visible_group_ids_for_user(user_id, owner_group_id, all_group_ids, cache)
            return _PasswordAccessEntry(
                password,
                owner_group_id,
                can_read=True,
                can_write=user_access.can_write,
                visible_group_ids=visible_ids,
                access_expires_at=user_access.expires_at,
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
            access_expires_at=entry.access_expires_at,
        )

    def _find_owner_group_id(self, permissions: GroupPermissions) -> UUID | None:
        return next((gid for gid, access in permissions.items() if access.is_owner), None)

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
        now: datetime,
    ) -> _UserAccess | None:
        temporary: _UserAccess | None = None

        for group_id, access in permissions.items():
            if not access.grants_read(now) or not self._user_belongs_to_group(user_id, group_id, cache):
                continue
            if access.is_owner:
                return _UserAccess(can_write=True, expires_at=None)
            # Keep looking: a permanent share elsewhere, or ownership, outranks
            # this one, and the user should not be warned about a deadline that
            # does not actually end their access.
            if temporary is None or self._outlasts(access.expires_at, temporary.expires_at):
                temporary = _UserAccess(can_write=False, expires_at=access.expires_at)

        return temporary

    @staticmethod
    def _outlasts(candidate: datetime | None, current: datetime | None) -> bool:
        if candidate is None:
            return True
        if current is None:
            return False
        return candidate > current

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

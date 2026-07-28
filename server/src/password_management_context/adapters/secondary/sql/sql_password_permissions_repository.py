from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, col, delete, select

from password_management_context.adapters.secondary.sql import (
    OwnershipTable,
    PermissionsTable,
)
from password_management_context.application.gateways.password_permissions_repository import (
    BulkGroupPermissions,
    GroupPermissions,
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects.password_group_access import (
    PasswordGroupAccess,
)
from password_management_context.domain.value_objects.password_permission import (
    PasswordPermission,
)
from shared_kernel.adapters.secondary.sql import SQLBaseRepository, as_utc, to_naive_utc


def _merge_expiry(current: datetime | None, candidate: datetime | None, is_first: bool) -> datetime | None:
    """Fold several permission rows for one group into a single deadline.

    A group keeps access for as long as any of its rows is still alive, so the
    furthest date wins and a permanent row (None) beats every date. Only READ
    exists today, so in practice there is never more than one row to fold.
    """
    if is_first:
        return candidate
    if current is None or candidate is None:
        return None
    return max(current, candidate)


class SqlPasswordPermissionsRepository(SQLBaseRepository, PasswordPermissionsRepository):
    """SQL implementation of PasswordPermissionsRepository using shared tables"""

    def __init__(self, session: Session):
        super().__init__(session)

    def set_owner(self, owner_id: UUID, password_id: UUID) -> None:
        """Set a group as the owner of a password"""
        # Check if ownership already exists
        statement = select(OwnershipTable).where(
            OwnershipTable.group_id == owner_id,
            OwnershipTable.resource_id == password_id,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            ownership = OwnershipTable(group_id=owner_id, resource_id=password_id)
            self._session.add(ownership)
            self.commit()

    def is_owner(self, owner_id: UUID, password_id: UUID) -> bool:
        """Check if a group is the owner of a password"""
        statement = select(OwnershipTable).where(
            OwnershipTable.group_id == owner_id,
            OwnershipTable.resource_id == password_id,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def has_access(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> bool:
        """Check if a group has access to a password, ignoring expiry"""
        # Check if group is the owner
        if self.is_owner(group_id, password_id):
            return True

        # Check if group has explicit permissions
        statement = select(PermissionsTable).where(
            PermissionsTable.group_id == group_id,
            PermissionsTable.resource_id == password_id,
            PermissionsTable.permission == permission.value,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def grant_access(
        self,
        group_id: UUID,
        password_id: UUID,
        permission: PasswordPermission,
        expires_at: datetime | None = None,
    ) -> None:
        """Grant a permission to a group, permanently or until expires_at"""
        statement = select(PermissionsTable).where(
            PermissionsTable.group_id == group_id,
            PermissionsTable.resource_id == password_id,
            PermissionsTable.permission == permission.value,
        )
        existing = self._session.exec(statement).first()

        if existing:
            # Re-sharing is how a duration is (re)set on an already-shared group;
            # leaving the row untouched would silently drop the new deadline.
            existing.expires_at = to_naive_utc(expires_at)
            self._session.add(existing)
        else:
            self._session.add(
                PermissionsTable(
                    group_id=group_id,
                    resource_id=password_id,
                    permission=permission.value,
                    expires_at=to_naive_utc(expires_at),
                )
            )

        self.commit()

    def update_access_expiration(self, group_id: UUID, password_id: UUID, expires_at: datetime | None) -> bool:
        """Change when an existing share expires; None makes it permanent"""
        statement = select(PermissionsTable).where(
            PermissionsTable.group_id == group_id,
            PermissionsTable.resource_id == password_id,
        )
        permission_entries = self._session.exec(statement).all()

        if not permission_entries:
            return False

        for permission_entry in permission_entries:
            permission_entry.expires_at = to_naive_utc(expires_at)
            self._session.add(permission_entry)

        self.commit()
        return True

    def revoke_access(self, group_id: UUID, password_id: UUID) -> None:
        """Revoke all permissions from a group for a password"""
        statement = select(PermissionsTable).where(
            PermissionsTable.group_id == group_id,
            PermissionsTable.resource_id == password_id,
        )
        permission_entries = self._session.exec(statement).all()

        for permission_entry in permission_entries:
            self._session.delete(permission_entry)

        if permission_entries:
            self.commit()

    def purge_expired_shares(self, cutoff: datetime) -> int:
        """Delete shares that expired before cutoff, returning how many were removed"""
        statement = delete(PermissionsTable).where(
            col(PermissionsTable.expires_at).is_not(None),
            col(PermissionsTable.expires_at) < to_naive_utc(cutoff),
        )
        result = self._session.exec(statement)

        # Commit unconditionally rather than keying the commit off rowcount.
        # DBAPIs are only required to report a best effort there (PEP 249 allows
        # -1 for "cannot be determined"), and the session is request-scoped and
        # closes with a rollback, so a skipped commit would silently undo the
        # purge instead of merely miscounting it.
        self.commit()

        rowcount = result.rowcount
        return rowcount if isinstance(rowcount, int) and rowcount > 0 else 0

    def list_all_permissions_for(self, password_id: UUID) -> GroupPermissions:
        """Get all groups who have access to a password with their permissions"""
        ownership_statement = select(OwnershipTable).where(OwnershipTable.resource_id == password_id)
        owner_group_ids = {ownership.group_id for ownership in self._session.exec(ownership_statement).all()}

        permission_statement = select(PermissionsTable).where(PermissionsTable.resource_id == password_id)
        permission_rows = self._session.exec(permission_statement).all()

        return self._assemble(owner_group_ids, permission_rows)

    def list_all_permissions_for_bulk(self, password_ids: list[UUID]) -> BulkGroupPermissions:
        """Get all group permissions for multiple passwords in two SQL queries."""
        owner_group_ids: dict[UUID, set[UUID]] = {pwd_id: set() for pwd_id in password_ids}
        permission_rows: dict[UUID, list[PermissionsTable]] = {pwd_id: [] for pwd_id in password_ids}

        ownership_statement = select(OwnershipTable).where(OwnershipTable.resource_id.in_(password_ids))
        for ownership in self._session.exec(ownership_statement).all():
            owner_group_ids[ownership.resource_id].add(ownership.group_id)

        permission_statement = select(PermissionsTable).where(PermissionsTable.resource_id.in_(password_ids))
        for permission_row in self._session.exec(permission_statement).all():
            permission_rows[permission_row.resource_id].append(permission_row)

        return {pwd_id: self._assemble(owner_group_ids[pwd_id], permission_rows[pwd_id]) for pwd_id in password_ids}

    @staticmethod
    def _assemble(owner_group_ids: set[UUID], permission_rows: Iterable[PermissionsTable]) -> GroupPermissions:
        """Fold ownership rows and permission rows into one access object per group"""
        permissions: dict[UUID, set[PasswordPermission]] = {group_id: set() for group_id in owner_group_ids}
        expiries: dict[UUID, datetime | None] = {}

        for row in permission_rows:
            try:
                permission = PasswordPermission(row.permission)
            except ValueError:
                # Skip invalid permissions
                continue

            is_first = row.group_id not in expiries
            permissions.setdefault(row.group_id, set()).add(permission)
            expiries[row.group_id] = _merge_expiry(expiries.get(row.group_id), as_utc(row.expires_at), is_first)

        return {
            group_id: PasswordGroupAccess(
                is_owner=group_id in owner_group_ids,
                permissions=group_permissions,
                expires_at=expiries.get(group_id),
            )
            for group_id, group_permissions in permissions.items()
        }

    def has_any_password_for_group(self, group_id: UUID) -> bool:
        """Check if a group has any password (as owner or with access)"""
        ownership_statement = select(OwnershipTable).where(
            OwnershipTable.group_id == group_id,
        )
        ownership_result = self._session.exec(ownership_statement).first()
        if ownership_result:
            return True

        # Check if group has any permissions for existing passwords
        permission_statement = select(PermissionsTable).where(
            PermissionsTable.group_id == group_id,
        )
        permission_result = self._session.exec(permission_statement).first()
        return permission_result is not None

    def revoke_all_access_for_password(self, password_id: UUID):
        """Revoke all access (permissions and ownerships) for a specific password"""
        ownership_statement = select(OwnershipTable).where(OwnershipTable.resource_id == password_id)
        ownership_entries = self._session.exec(ownership_statement).all()
        for ownership_entry in ownership_entries:
            self._session.delete(ownership_entry)

        permission_statement = select(PermissionsTable).where(
            PermissionsTable.resource_id == password_id,
        )
        permission_entries = self._session.exec(permission_statement).all()
        for permission_entry in permission_entries:
            self._session.delete(permission_entry)

        self.commit()

    def revoke_all_access_for_owner_group(self, group_id: UUID) -> None:
        """Revoke all access for all passwords owned by a group in one SQL operation"""
        # First, get all password IDs owned by this group
        ownership_select = select(OwnershipTable.resource_id).where(OwnershipTable.group_id == group_id)
        password_ids = list(self._session.exec(ownership_select).all())

        if not password_ids:
            return

        # Delete all ownerships for these passwords
        ownership_statement = select(OwnershipTable).where(OwnershipTable.resource_id.in_(password_ids))
        ownership_entries = self._session.exec(ownership_statement).all()
        for ownership_entry in ownership_entries:
            self._session.delete(ownership_entry)

        # Delete all permissions for these passwords
        permission_statement = select(PermissionsTable).where(PermissionsTable.resource_id.in_(password_ids))
        permission_entries = self._session.exec(permission_statement).all()
        for permission_entry in permission_entries:
            self._session.delete(permission_entry)

        if ownership_entries or permission_entries:
            self.commit()

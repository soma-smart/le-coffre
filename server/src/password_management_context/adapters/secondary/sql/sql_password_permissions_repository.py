from uuid import UUID

from sqlmodel import Session, select

from password_management_context.adapters.secondary.sql import (
    OwnershipTable,
    PermissionsTable,
)
from password_management_context.application.gateways.password_permissions_repository import (
    BulkGroupPermissions,
    GroupPermissions,
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects.password_permission import (
    PasswordPermission,
)
from shared_kernel.adapters.secondary.sql import SQLBaseRepository


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
        """Check if a group has access to a password"""
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

    def grant_access(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> None:
        """Grant a specific permission to a group for a password"""
        # Check if permission already exists
        statement = select(PermissionsTable).where(
            PermissionsTable.group_id == group_id,
            PermissionsTable.resource_id == password_id,
            PermissionsTable.permission == permission.value,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            permission_entry = PermissionsTable(
                group_id=group_id,
                resource_id=password_id,
                permission=permission.value,
            )
            self._session.add(permission_entry)
            self.commit()

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

    def list_all_permissions_for(self, password_id: UUID) -> GroupPermissions:
        """Get all groups who have access to a password with their permissions"""
        result: GroupPermissions = {}

        # Get all owner groups
        ownership_statement = select(OwnershipTable).where(OwnershipTable.resource_id == password_id)
        ownerships = self._session.exec(ownership_statement).all()
        for ownership in ownerships:
            if ownership.group_id not in result:
                result[ownership.group_id] = (True, set())

        # Get all groups with permissions
        permission_statement = select(PermissionsTable).where(PermissionsTable.resource_id == password_id)
        permissions = self._session.exec(permission_statement).all()
        for permission_entry in permissions:
            if permission_entry.group_id not in result:
                result[permission_entry.group_id] = (False, set())
            try:
                result[permission_entry.group_id][1].add(PasswordPermission(permission_entry.permission))
            except ValueError:
                # Skip invalid permissions
                pass

        return result

    def list_all_permissions_for_bulk(self, password_ids: list[UUID]) -> BulkGroupPermissions:
        """Get all group permissions for multiple passwords in two SQL queries."""
        result: BulkGroupPermissions = {pwd_id: {} for pwd_id in password_ids}

        ownership_statement = select(OwnershipTable).where(OwnershipTable.resource_id.in_(password_ids))
        for ownership in self._session.exec(ownership_statement).all():
            result[ownership.resource_id][ownership.group_id] = (True, set())

        permission_statement = select(PermissionsTable).where(PermissionsTable.resource_id.in_(password_ids))
        for perm_entry in self._session.exec(permission_statement).all():
            pwd_perms = result[perm_entry.resource_id]
            if perm_entry.group_id not in pwd_perms:
                pwd_perms[perm_entry.group_id] = (False, set())
            try:
                pwd_perms[perm_entry.group_id][1].add(PasswordPermission(perm_entry.permission))
            except ValueError:
                pass

        return result

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

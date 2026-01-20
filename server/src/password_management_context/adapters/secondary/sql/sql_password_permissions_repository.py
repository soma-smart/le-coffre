from uuid import UUID
from sqlmodel import select

from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects.password_permission import (
    PasswordPermission,
)
from password_management_context.adapters.secondary.sql import (
    PermissionsTable,
    OwnershipTable,
)


class SqlPasswordPermissionsRepository(PasswordPermissionsRepository):
    """SQL implementation of PasswordPermissionsRepository using shared tables"""

    def __init__(self, Session):
        self._session = Session

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
            self._session.commit()

    def is_owner(self, owner_id: UUID, password_id: UUID) -> bool:
        """Check if a group is the owner of a password"""
        statement = select(OwnershipTable).where(
            OwnershipTable.group_id == owner_id,
            OwnershipTable.resource_id == password_id,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def has_access(
        self, group_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> bool:
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

    def grant_access(
        self, group_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> None:
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
            self._session.commit()

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
            self._session.commit()

    def list_all_permissions_for(
        self, password_id: UUID
    ) -> dict[UUID, tuple[bool, set[PasswordPermission]]]:
        """Get all groups who have access to a password with their permissions"""
        result: dict[UUID, tuple[bool, set[PasswordPermission]]] = {}

        # Get all owner groups
        ownership_statement = select(OwnershipTable).where(
            OwnershipTable.resource_id == password_id
        )
        ownerships = self._session.exec(ownership_statement).all()
        for ownership in ownerships:
            if ownership.group_id not in result:
                result[ownership.group_id] = (True, set())

        # Get all groups with permissions
        permission_statement = select(PermissionsTable).where(
            PermissionsTable.resource_id == password_id
        )
        permissions = self._session.exec(permission_statement).all()
        for permission_entry in permissions:
            if permission_entry.group_id not in result:
                result[permission_entry.group_id] = (False, set())
            try:
                result[permission_entry.group_id][1].add(
                    PasswordPermission(permission_entry.permission)
                )
            except ValueError:
                # Skip invalid permissions
                pass

        return result

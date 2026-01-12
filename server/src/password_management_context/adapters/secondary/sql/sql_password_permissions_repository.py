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

    def set_owner(self, user_id: UUID, password_id: UUID) -> None:
        """Set a user as the owner of a password"""
        # Check if ownership already exists
        statement = select(OwnershipTable).where(
            OwnershipTable.user_id == user_id,
            OwnershipTable.resource_id == password_id,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            ownership = OwnershipTable(user_id=user_id, resource_id=password_id)
            self._session.add(ownership)
            self._session.commit()

    def is_owner(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if a user is the owner of a password"""
        statement = select(OwnershipTable).where(
            OwnershipTable.user_id == user_id,
            OwnershipTable.resource_id == password_id,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def has_access(
        self, user_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> bool:
        """Check if a user has any access to a password"""
        # User has access if they are the owner OR have explicit permissions
        if self.is_owner(user_id, password_id):
            return True

        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == password_id,
            PermissionsTable.permission == permission.value,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def grant_access(
        self, user_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> None:
        """Grant a specific permission to a user for a password"""
        # Check if permission already exists
        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == password_id,
            PermissionsTable.permission == permission.value,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            permission_entry = PermissionsTable(
                user_id=user_id,
                resource_id=password_id,
                permission=permission.value,
            )
            self._session.add(permission_entry)
            self._session.commit()

    def revoke_access(self, user_id: UUID, password_id: UUID) -> None:
        """Revoke all permissions from a user for a password"""
        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
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
        """Get all users who have access to a password with their permissions"""
        result: dict[UUID, tuple[bool, set[PasswordPermission]]] = {}

        # Get all owners
        ownership_statement = select(OwnershipTable).where(
            OwnershipTable.resource_id == password_id
        )
        ownerships = self._session.exec(ownership_statement).all()
        for ownership in ownerships:
            if ownership.user_id not in result:
                result[ownership.user_id] = (True, set())

        # Get all users with permissions
        permission_statement = select(PermissionsTable).where(
            PermissionsTable.resource_id == password_id
        )
        permissions = self._session.exec(permission_statement).all()
        for permission_entry in permissions:
            if permission_entry.user_id not in result:
                result[permission_entry.user_id] = (False, set())
            try:
                result[permission_entry.user_id][1].add(
                    PasswordPermission(permission_entry.permission)
                )
            except ValueError:
                # Skip invalid permissions
                pass

        return result

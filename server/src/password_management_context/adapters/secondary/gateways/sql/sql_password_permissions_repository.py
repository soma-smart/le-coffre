from typing import List
from uuid import UUID
from sqlmodel import select

from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects.password_permission import (
    PasswordPermission,
)
from rights_access_context.adapters.secondary.sql.model.rights_model import (
    PermissionsTable,
    OwnershipsTable,
)


class SqlPasswordPermissionsRepository(PasswordPermissionsRepository):
    """SQL implementation of PasswordPermissionsRepository using shared tables"""

    def __init__(self, Session):
        self._session = Session

    def set_owner(self, user_id: UUID, password_id: UUID) -> None:
        """Set a user as the owner of a password"""
        # Check if ownership already exists
        statement = select(OwnershipsTable).where(
            OwnershipsTable.user_id == user_id,
            OwnershipsTable.resource_id == password_id,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            ownership = OwnershipsTable(user_id=user_id, resource_id=password_id)
            self._session.add(ownership)
            self._session.commit()

    def is_owner(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if a user is the owner of a password"""
        statement = select(OwnershipsTable).where(
            OwnershipsTable.user_id == user_id,
            OwnershipsTable.resource_id == password_id,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def has_access(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if a user has any access to a password"""
        # User has access if they are the owner OR have explicit permissions
        if self.is_owner(user_id, password_id):
            return True

        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == password_id,
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

    def revoke_access(
        self, user_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> None:
        """Revoke a specific permission from a user for a password"""
        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == password_id,
            PermissionsTable.permission == permission.value,
        )
        permission_entry = self._session.exec(statement).first()

        if permission_entry:
            self._session.delete(permission_entry)
            self._session.commit()

    def get_all_users_with_access(self, password_id: UUID) -> List[UUID]:
        """Get all user IDs that have any kind of access to a password"""
        user_ids = set()

        # Get all owners
        ownership_statement = select(OwnershipsTable).where(
            OwnershipsTable.resource_id == password_id
        )
        ownerships = self._session.exec(ownership_statement).all()
        for ownership in ownerships:
            user_ids.add(ownership.user_id)

        # Get all users with permissions
        permission_statement = select(PermissionsTable).where(
            PermissionsTable.resource_id == password_id
        )
        permissions = self._session.exec(permission_statement).all()
        for permission in permissions:
            user_ids.add(permission.user_id)

        return list(user_ids)

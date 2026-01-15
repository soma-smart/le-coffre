from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from rights_access_context.application.gateways import RightsRepository
from rights_access_context.domain.value_objects import Permission

from .model.rights_model import OwnershipsTable, PermissionsTable


class SqlRightsRepository(RightsRepository):
    def __init__(self, Session):
        self._session = Session

    def add_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> None:
        # Check if permission already exists
        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == resource_id,
            PermissionsTable.permission == permission.value,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            db_obj = PermissionsTable(
                user_id=user_id,
                resource_id=resource_id,
                permission=permission.value,
            )
            self._session.add(db_obj)
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()

    def remove_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> None:
        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == resource_id,
            PermissionsTable.permission == permission.value,
        )
        result = self._session.exec(statement).first()

        if result:
            self._session.delete(result)
            self._session.commit()

    def has_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> bool:
        if self.is_owner(user_id, resource_id):
            return True

        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == resource_id,
            PermissionsTable.permission == permission.value,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def get_all_permissions(self, user_id: UUID, resource_id: UUID) -> set[Permission]:
        statement = select(PermissionsTable).where(
            PermissionsTable.user_id == user_id,
            PermissionsTable.resource_id == resource_id,
        )
        results = self._session.exec(statement).all()

        permissions = set()
        for result in results:
            try:
                permissions.add(Permission(result.permission))
            except ValueError:
                # Skip invalid permissions
                continue

        return permissions

    def set_owner(self, user_id: UUID, resource_id: UUID) -> None:
        # Check if ownership already exists
        statement = select(OwnershipsTable).where(
            OwnershipsTable.user_id == user_id,
            OwnershipsTable.resource_id == resource_id,
        )
        existing = self._session.exec(statement).first()

        if not existing:
            db_obj = OwnershipsTable(
                user_id=user_id,
                resource_id=resource_id,
            )
            self._session.add(db_obj)
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()

    def is_owner(self, user_id: UUID, resource_id: UUID) -> bool:
        statement = select(OwnershipsTable).where(
            OwnershipsTable.user_id == user_id,
            OwnershipsTable.resource_id == resource_id,
        )
        result = self._session.exec(statement).first()
        return result is not None

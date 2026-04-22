from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.password import PasswordTable


class SqlPasswordRepository(SQLBaseRepository, PasswordRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def save(self, password: Password) -> None:
        """Save a password entity"""
        db_obj = PasswordTable.model_validate(password)
        self._session.add(db_obj)
        self.commit_and_refresh(db_obj)

    def get_by_id(self, id: UUID) -> Password:
        """Get password by UUID"""
        statement = select(PasswordTable).where(PasswordTable.id == id)
        result = self._session.exec(statement).first()
        if result is None:
            raise PasswordNotFoundError(id)
        return result

    def list_all(self, folder: str | None = None) -> list[Password]:
        """List all passwords"""
        statement = select(PasswordTable)
        if folder:
            statement = statement.where(PasswordTable.folder == folder)
        results = self._session.exec(statement).all()
        return results

    def delete(self, id: UUID) -> None:
        """Delete password by UUID"""
        statement = select(PasswordTable).where(PasswordTable.id == id)
        db_obj = self._session.exec(statement).first()
        if db_obj is None:
            raise PasswordNotFoundError(id)
        if db_obj:
            self._session.delete(db_obj)
            self.commit()

    def delete_by_owner_group(self, group_id: UUID) -> None:
        """Delete all passwords owned by a specific group in one SQL operation"""
        from password_management_context.adapters.secondary.sql import OwnershipTable

        # First, get all password IDs owned by this group
        ownership_statement = select(OwnershipTable.resource_id).where(OwnershipTable.group_id == group_id)
        password_ids = list(self._session.exec(ownership_statement).all())

        if not password_ids:
            return

        # Delete all passwords in one query
        delete_statement = select(PasswordTable).where(PasswordTable.id.in_(password_ids))
        passwords_to_delete = self._session.exec(delete_statement).all()

        for password in passwords_to_delete:
            self._session.delete(password)

        if passwords_to_delete:
            self._session.commit()

    def update(self, password: Password) -> None:
        """Update password"""
        statement = select(PasswordTable).where(PasswordTable.id == password.id)
        db_obj = self._session.exec(statement).first()
        if db_obj is None:
            raise PasswordNotFoundError(password.id)
        if db_obj:
            for field, value in vars(password).items():
                setattr(db_obj, field, value)
            self._session.add(db_obj)
            self.commit_and_refresh(db_obj)

    def count(self) -> int:
        """Return total number of passwords"""
        statement = select(func.count()).select_from(PasswordTable)
        return self._session.exec(statement).one()

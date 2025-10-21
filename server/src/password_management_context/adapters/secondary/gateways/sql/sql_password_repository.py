from typing import List, Optional, Protocol
from uuid import UUID
from .model.password import PasswordTable
from sqlmodel import Session, select
from password_management_context.domain.exceptions import PasswordNotFoundError

from password_management_context.domain.entities import Password
from password_management_context.application.gateways import PasswordRepository

class SqlPasswordRepository(PasswordRepository):
    def __init__(self, Session):
        self._session = Session
        
    def save(self, password: Password) -> None:
        """Save a password entity"""
        db_obj = PasswordTable.model_validate(password)
        self._session.add(db_obj)
        self._session.commit()
        self._session.refresh(db_obj)
        return db_obj

    def get_by_id(self, id: UUID) -> Password:
        """Get password by UUID"""
        statement = select(PasswordTable).where(PasswordTable.id == id)
        result = self._session.exec(statement).first()
        if result is None:
            raise PasswordNotFoundError(id)
        return result

    def list_all(self, folder: Optional[str] = None) -> List[Password]:
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
        if db_obj:
            self._session.delete(db_obj)
            self._session.commit()

    def update(self, password: Password) -> None:
        """Update password"""
        statement = select(PasswordTable).where(PasswordTable.id == password.id)
        db_obj = self._session.exec(statement).first()
        if db_obj:
            for field, value in vars(password).items():
                setattr(db_obj, field, value)
            self._session.add(db_obj)
            self._session.commit()
            self._session.refresh(db_obj)
        return db_obj

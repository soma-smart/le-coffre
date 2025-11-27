from typing import Optional, Dict
from uuid import UUID
from identity_access_management_context.domain.entities.sso_user import SsoUser
from sqlmodel import select
from .model.sso_users_model import SsoUsersTable
from sqlalchemy.exc import IntegrityError

from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
    SsoUserAlreadyExistsException
)


class SqlSsoUserRepository:
    def __init__(self, Session):
        self._sessions = Session

    def save(self, sso_user: SsoUser) -> None:
        data = {k: v for k, v in vars(sso_user).items() if v is not None} #Creating a dictionary without None values
        db_obj =  SsoUsersTable(**data)
        self._sessions.add(db_obj)
        try:
            self._sessions.commit()
            self._sessions.refresh(db_obj)
        except IntegrityError:
            self._sessions.rollback()
            raise SsoUserAlreadyExistsException("SSO User already exists")  

    def get_by_sso_user_id(self, sso_user_id: str, sso_provider: str = "default") -> Optional[SsoUser]:
        statement = select(SsoUsersTable).where(
            SsoUsersTable.sso_user_id == str(sso_user_id),
            SsoUsersTable.sso_provider == sso_provider
        )
        results = self._sessions.exec(statement).first()
        return results
      
    def get_by_user_id(self, user_id: UUID) -> Optional[SsoUser]:
        statement = select(SsoUsersTable).where(
            SsoUsersTable.internal_user_id == user_id
        )
        results = self._sessions.exec(statement).first()
        if results is None:
            raise UserNotFoundError(user_id)
        return results

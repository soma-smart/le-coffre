from typing import Optional, Dict
from uuid import UUID
from identity_access_management_context.domain.entities.sso_user import SsoUser
from sqlmodel import select
from .model.sso_users_model import SsoUsersTable

from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
)


class InMemorySsoUserRepository:
    def __init__(self, Session):
        self._sessions = Session

    def save(self, sso_user: SsoUser) -> None:
        db_obj =  SsoUsersTable.model_validate(sso_user)
        self._sessions.add(db_obj)
        self._sessions.commit()
        self._sessions.refresh(db_obj)
        if not db_obj:
            raise UserAlreadyExistsError(sso_user.sso_user_id)  

    def get_by_sso_user_id(
        self, sso_user_id: str, sso_provider: str = "default"
    ) -> Optional[SsoUser]:
        statement = select(SsoUsersTable).where(
            SsoUsersTable.sso_user_id == sso_user_id,
            SsoUsersTable.sso_provider == sso_provider
        )
        results = self._sessions.exec(statement).first()
        if results is None:
            raise UserNotFoundError(sso_user_id)
        return results
      
    def get_by_user_id(self, user_id: UUID) -> Optional[SsoUser]:
        statement = select(SsoUsersTable).where(
            SsoUsersTable.internal_user_id == user_id
        )
        results = self._sessions.exec(statement).first()
        if results is None:
            raise UserNotFoundError(user_id)
        return results

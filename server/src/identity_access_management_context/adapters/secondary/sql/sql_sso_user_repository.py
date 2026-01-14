from typing import Optional
from uuid import UUID
from identity_access_management_context.domain.entities.sso_user import SsoUser
from sqlmodel import select
from .model.sso_users_model import SsoUsersTable
from sqlalchemy.exc import IntegrityError

from identity_access_management_context.domain.exceptions import (
    SsoUserAlreadyExistsException,
)


class SqlSsoUserRepository:
    def __init__(self, Session):
        self._session = Session

    def save(self, sso_user: SsoUser) -> None:
        data = {
            k: v for k, v in vars(sso_user).items() if v is not None
        }  # Creating a dictionary without None values
        db_obj = SsoUsersTable(**data)
        exist = self.get_by_sso_user_id(
            sso_user.sso_user_id, sso_user.sso_provider
        )
        if exist is None:
            self._session.add(db_obj)
            self._session.commit()
            self._session.refresh(db_obj)
        else:
            pass  # or update logic if needed
            


    def get_by_sso_user_id(
        self, sso_user_id: str, sso_provider: str = "default"
    ) -> Optional[SsoUser]:
        statement = select(SsoUsersTable).where(
            SsoUsersTable.sso_user_id == str(sso_user_id),
            SsoUsersTable.sso_provider == sso_provider,
        )
        results = self._session.exec(statement).first()
        return results

    def get_by_user_id(self, user_id: UUID) -> Optional[SsoUser]:
        statement = select(SsoUsersTable).where(
            SsoUsersTable.internal_user_id == user_id
        )
        results = self._session.exec(statement).first()
        return results

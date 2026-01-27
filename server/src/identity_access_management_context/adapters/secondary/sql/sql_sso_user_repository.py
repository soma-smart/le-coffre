from datetime import datetime
from typing import Optional
from uuid import UUID
from identity_access_management_context.domain.entities.sso_user import SsoUser
from sqlmodel import select, Session
from .model.sso_users_model import SsoUsersTable

from identity_access_management_context.domain.exceptions import (
    SsoUserAlreadyExistsException,
)


class SqlSsoUserRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, sso_user: SsoUser) -> None:
        exist = self.get_by_sso_user_id(sso_user.sso_user_id, sso_user.sso_provider)
        if exist is not None:
            raise SsoUserAlreadyExistsException(
                f"SSO user {sso_user.sso_user_id} with provider {sso_user.sso_provider} already exists"
            )

        data = {
            k: v for k, v in vars(sso_user).items() if v is not None
        }  # Creating a dictionary without None values
        db_obj = SsoUsersTable(**data)
        self._session.add(db_obj)
        self._session.commit()
        self._session.refresh(db_obj)

    def update_last_login(
        self, sso_user_id: str, sso_provider: str, last_login: datetime
    ) -> None:
        db_obj = self.get_by_sso_user_id(sso_user_id, sso_provider)
        if db_obj is not None:
            db_obj.last_login = last_login
            self._session.commit()
            self._session.refresh(db_obj)

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

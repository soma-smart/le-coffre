from typing import Optional
from uuid import UUID
from sqlmodel import select, Session
from identity_access_management_context.adapters.secondary.sql.model.user_password_model import (
    UserPasswordTable,
)
from identity_access_management_context.domain.entities import UserPassword
from shared_kernel.adapters.secondary.sql import SQLBaseRepository


class SqlUserPasswordRepository(SQLBaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def save(self, user_password: UserPassword) -> None:
        user_password_table = UserPasswordTable(
            id=user_password.id,
            email=user_password.email,
            password_hash=user_password.password_hash,
            display_name=user_password.display_name,
        )
        self._session.add(user_password_table)
        self.commit()

    def update(self, user_password: UserPassword) -> None:
        user_password_table = self._session.exec(
            select(UserPasswordTable).where(UserPasswordTable.id == user_password.id)
        ).first()
        if user_password_table:
            user_password_table.email = user_password.email
            user_password_table.password_hash = user_password.password_hash
            user_password_table.display_name = user_password.display_name
            self._session.add(user_password_table)
            self.commit()

    def get_by_id(self, id: UUID) -> Optional[UserPassword]:
        user_password_table = self._session.exec(
            select(UserPasswordTable).where(UserPasswordTable.id == id)
        ).first()
        if user_password_table:
            return UserPassword(
                id=user_password_table.id,
                email=user_password_table.email,
                password_hash=user_password_table.password_hash,
                display_name=user_password_table.display_name,
            )
        return None

    def get_by_email(self, email: str) -> Optional[UserPassword]:
        user_password_table = self._session.exec(
            select(UserPasswordTable).where(UserPasswordTable.email == email)
        ).first()
        if user_password_table:
            return UserPassword(
                id=user_password_table.id,
                email=user_password_table.email,
                password_hash=user_password_table.password_hash,
                display_name=user_password_table.display_name,
            )
        return None

import json
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.domain.value_objects.constants import ADMIN_ROLE

from .model.users_model import UserTable


class SqlUserRepository(SQLBaseRepository, UserRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(UserTable).where(UserTable.id == user_id)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return User(
            id=result.id,
            username=result.username,
            email=result.email,
            name=result.name,
            roles=json.loads(result.roles),
        )

    def get_by_email(self, email: str) -> list[User]:
        statement = select(UserTable).where(UserTable.email == email)
        results = self._session.exec(statement).all()
        if not results:
            return []
        return [
            User(
                id=row.id,
                username=row.username,
                email=row.email,
                name=row.name,
                roles=json.loads(row.roles),
            )
            for row in results
        ]

    def list_all(self) -> list[User]:
        statement = select(UserTable)
        results = self._session.exec(statement).all()
        if not results:
            return []
        return [
            User(
                id=row.id,
                username=row.username,
                email=row.email,
                name=row.name,
                roles=json.loads(row.roles),
            )
            for row in results
        ]

    def save(self, user: User) -> None:
        user_dict = vars(user).copy()
        user_dict["roles"] = json.dumps(user.roles)
        db_obj = UserTable(**user_dict)
        self._session.add(db_obj)
        try:
            self.commit_and_refresh(db_obj)
        except IntegrityError as e:
            raise UserAlreadyExistsError(user.username) from e

    def delete(self, user_id: UUID) -> None:
        statement = select(UserTable).where(UserTable.id == user_id)
        db_obj = self._session.exec(statement).first()
        if db_obj is None:
            raise UserNotFoundError(user_id)
        self._session.delete(db_obj)
        self.commit()

    def update(self, user: User) -> None:
        statement = select(UserTable).where(UserTable.id == user.id)
        db_obj = self._session.exec(statement).first()
        if db_obj is None:
            raise UserNotFoundError(user.id)
        for key, value in vars(user).items():
            if key == "roles":
                value = json.dumps(value)
            setattr(db_obj, key, value)
        self._session.add(db_obj)
        self.commit_and_refresh(db_obj)

    def count(self) -> int:
        statement = select(func.count()).select_from(UserTable)
        return self._session.exec(statement).one()

    def get_admin(self) -> User | None:
        statement = select(UserTable).where(UserTable.roles.like(f'%"{ADMIN_ROLE}"%'))
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return User(
            id=result.id,
            username=result.username,
            email=result.email,
            name=result.name,
            roles=json.loads(result.roles),
        )

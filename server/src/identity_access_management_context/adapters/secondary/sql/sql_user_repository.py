import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import String, cast, func, or_
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

from .model.principal_model import PrincipalKind, PrincipalTable
from .model.users_model import UserPrincipalTable


class SqlUserRepository(SQLBaseRepository, UserRepository):
    """Users, stored as a principal registry row plus their user details."""

    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(UserPrincipalTable).where(UserPrincipalTable.principal_id == user_id)
        row = self._session.exec(statement).first()
        return self._to_entity(row) if row is not None else None

    def get_by_email(self, email: str) -> list[User]:
        statement = select(UserPrincipalTable).where(UserPrincipalTable.email == email)
        return [self._to_entity(row) for row in self._session.exec(statement).all()]

    def count(self) -> int:
        """Count users."""
        statement = select(func.count()).select_from(UserPrincipalTable)
        return self._session.exec(statement).one()

    def list_all(self) -> list[User]:
        statement = select(UserPrincipalTable)
        return [self._to_entity(row) for row in self._session.exec(statement).all()]

    def search(self, query: str) -> list[User]:
        pattern = f"%{self._escape_like(query)}%"
        statement = select(UserPrincipalTable).where(
            or_(
                UserPrincipalTable.name.ilike(pattern, escape="\\"),  # type: ignore[attr-defined]
                UserPrincipalTable.username.ilike(pattern, escape="\\"),  # type: ignore[attr-defined]
                cast(UserPrincipalTable.principal_id, String).ilike(pattern, escape="\\"),
            )
        )
        return [self._to_entity(row) for row in self._session.exec(statement).all()]

    def save(self, user: User) -> None:
        # The registry row and the details are one principal: written together or not at all.
        self._session.add(PrincipalTable(id=user.id, kind=PrincipalKind.USER))
        db_obj = UserPrincipalTable(principal_id=user.id)
        self._apply(user, db_obj)
        self._session.add(db_obj)
        try:
            self.commit_and_refresh(db_obj)
        except IntegrityError as e:
            raise UserAlreadyExistsError(user.username) from e

    def delete(self, user_id: UUID) -> None:
        db_obj = self._session.get(UserPrincipalTable, user_id)
        if db_obj is None:
            raise UserNotFoundError(user_id)
        self._session.delete(db_obj)
        # Flushed first: the details reference the registry row.
        self._session.flush()
        principal = self._session.get(PrincipalTable, user_id)
        if principal is not None:
            self._session.delete(principal)
        self.commit()

    def update(self, user: User) -> None:
        db_obj = self._session.get(UserPrincipalTable, user.id)
        if db_obj is None:
            raise UserNotFoundError(user.id)
        self._apply(user, db_obj)
        self._session.add(db_obj)
        self.commit_and_refresh(db_obj)

    def get_admin(self) -> User | None:
        statement = select(UserPrincipalTable).where(UserPrincipalTable.roles.like(f'%"{ADMIN_ROLE}"%'))  # type: ignore[attr-defined]
        row = self._session.exec(statement).first()
        return self._to_entity(row) if row is not None else None

    @staticmethod
    def _apply(user: User, db_obj: UserPrincipalTable) -> None:
        """Copy the user's details onto its row."""
        db_obj.username = user.username
        db_obj.email = user.email
        db_obj.name = user.name
        db_obj.roles = json.dumps(user.roles)
        db_obj.current_refresh_token_jti = user.current_refresh_token_jti
        db_obj.session_invalid_before = user.session_invalid_before

    def _to_entity(self, row: UserPrincipalTable) -> User:
        return User(
            id=row.principal_id,
            username=row.username,
            email=row.email,
            name=row.name,
            roles=json.loads(row.roles),
            current_refresh_token_jti=row.current_refresh_token_jti,
            session_invalid_before=self._normalize_datetime(row.session_invalid_before),
        )

    def _normalize_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @staticmethod
    def _escape_like(value: str) -> str:
        """Escape LIKE/ILIKE wildcards so `search()` matches `query` literally."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

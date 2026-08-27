from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, col, func, select, update

from identity_access_management_context.adapters.secondary.sql.model.extension_token_model import (
    ExtensionTokenTable,
)
from identity_access_management_context.application.gateways import ExtensionTokenRepository
from identity_access_management_context.domain.entities import ExtensionToken
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc


class SqlExtensionTokenRepository(SQLBaseRepository, ExtensionTokenRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def add(self, token: ExtensionToken) -> ExtensionToken:
        db_obj = ExtensionTokenTable(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            device_name=token.device_name,
            created_at=to_naive_utc(token.created_at),
            expires_at=to_naive_utc(token.expires_at),
            last_used_at=to_naive_utc(token.last_used_at),
            revoked_at=to_naive_utc(token.revoked_at),
            created_from_ip=token.created_from_ip,
        )
        self._session.add(db_obj)
        self.commit_and_refresh(db_obj)
        return self._to_entity(db_obj)

    def get_by_token_hash(self, token_hash: str) -> ExtensionToken | None:
        statement = select(ExtensionTokenTable).where(ExtensionTokenTable.token_hash == token_hash)
        row = self._session.exec(statement).first()
        return self._to_entity(row) if row is not None else None

    def get_by_id(self, token_id: UUID) -> ExtensionToken | None:
        statement = select(ExtensionTokenTable).where(ExtensionTokenTable.id == token_id)
        row = self._session.exec(statement).first()
        return self._to_entity(row) if row is not None else None

    def list_for_user(self, user_id: UUID) -> list[ExtensionToken]:
        # Revoked and expired rows are returned too: the connected-devices
        # screen shows recent history, and the row is retained for audit.
        statement = (
            select(ExtensionTokenTable)
            .where(ExtensionTokenTable.user_id == user_id)
            .order_by(col(ExtensionTokenTable.created_at).desc())
        )
        return [self._to_entity(row) for row in self._session.exec(statement).all()]

    def count_active_for_user(self, user_id: UUID, now: datetime) -> int:
        statement = (
            select(func.count())
            .select_from(ExtensionTokenTable)
            .where(
                cast(Any, ExtensionTokenTable.user_id) == user_id,
                cast(Any, ExtensionTokenTable.revoked_at).is_(None),
                cast(Any, ExtensionTokenTable.expires_at) > to_naive_utc(now),
            )
        )
        return self._session.exec(statement).one()

    def revoke(self, token_id: UUID, now: datetime) -> bool:
        # Conditional UPDATE, so a second revoke leaves the original timestamp
        # alone and the audit trail keeps recording when access actually stopped.
        statement = (
            update(ExtensionTokenTable)
            .where(
                cast(Any, ExtensionTokenTable.id) == token_id,
                cast(Any, ExtensionTokenTable.revoked_at).is_(None),
            )
            .values(revoked_at=to_naive_utc(now))
        )
        result = self._session.exec(cast(Any, statement))
        self.commit()
        return cast(Any, result).rowcount == 1

    def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        statement = (
            update(ExtensionTokenTable)
            .where(
                cast(Any, ExtensionTokenTable.user_id) == user_id,
                cast(Any, ExtensionTokenTable.revoked_at).is_(None),
            )
            .values(revoked_at=to_naive_utc(now))
        )
        result = self._session.exec(cast(Any, statement))
        self.commit()
        return cast(Any, result).rowcount

    def touch_last_used(self, token_id: UUID, now: datetime, coarsen_to_seconds: int) -> None:
        # Coarsened so a busy extension does not write a row on every request:
        # the value only feeds a "last used" column in the UI, where minutes of
        # precision are ample.
        naive_now = to_naive_utc(now)
        threshold = naive_now - timedelta(seconds=coarsen_to_seconds)
        last_used_column = cast(Any, ExtensionTokenTable.last_used_at)
        statement = (
            update(ExtensionTokenTable)
            .where(
                cast(Any, ExtensionTokenTable.id) == token_id,
                last_used_column.is_(None) | (last_used_column < threshold),
            )
            .values(last_used_at=naive_now)
        )
        self._session.exec(cast(Any, statement))
        self.commit()

    def _to_entity(self, table: ExtensionTokenTable) -> ExtensionToken:
        return ExtensionToken(
            id=table.id,
            user_id=table.user_id,
            token_hash=table.token_hash,
            device_name=table.device_name,
            created_at=as_utc(table.created_at),
            expires_at=as_utc(table.expires_at),
            last_used_at=as_utc(table.last_used_at),
            revoked_at=as_utc(table.revoked_at),
            created_from_ip=table.created_from_ip,
        )

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import override
from uuid import UUID

from sqlalchemy import case, or_
from sqlmodel import Session, delete, select, update

from identity_access_management_context.application.gateways import (
    CannotRotateTokenCredentialError,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.domain.entities import TokenCredentialRecord
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc

from .model.credential_record import CredentialKind, CredentialRecordTable, TokenCredentialRecordTable
from .model.principal_model import PrincipalTable


class SqlTokenCredentialRecordRepository(SQLBaseRepository, TokenCredentialRecordRepository):
    """Token credential records, stored as a credential registry row plus the token details."""

    def __init__(self, session: Session):
        super().__init__(session)

    @staticmethod
    def _to_entity(registry: CredentialRecordTable, details: TokenCredentialRecordTable) -> TokenCredentialRecord:
        return TokenCredentialRecord(
            id=registry.id,
            principal_id=registry.principal_id,
            token_hash=details.token_hash,
            read_only=details.read_only,
            label=details.label,
            expires_at=as_utc(details.expires_at),
            last_used_at=as_utc(details.last_used_at),
            max_idle=None if details.max_idle_seconds is None else timedelta(seconds=details.max_idle_seconds),
        )

    def _find_all(self, *conditions) -> list[TokenCredentialRecord]:
        statement = (
            select(CredentialRecordTable, TokenCredentialRecordTable)
            .join(
                TokenCredentialRecordTable,
                TokenCredentialRecordTable.credential_id == CredentialRecordTable.id,  # pyright: ignore[reportArgumentType]
            )
            .where(*conditions)
        )
        return [self._to_entity(registry, details) for registry, details in self._session.exec(statement).all()]

    def _add(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        details = []
        for credential_record in credential_records:
            self._session.add(
                CredentialRecordTable(
                    id=credential_record.id,
                    kind=CredentialKind.TOKEN,
                    principal_id=credential_record.principal_id,
                )
            )
            details.append(
                TokenCredentialRecordTable(
                    credential_id=credential_record.id,
                    token_hash=credential_record.token_hash,
                    read_only=credential_record.read_only,
                    label=credential_record.label,
                    expires_at=to_naive_utc(credential_record.expires_at),
                    last_used_at=to_naive_utc(credential_record.last_used_at),
                    max_idle_seconds=None
                    if credential_record.max_idle is None
                    else int(credential_record.max_idle.total_seconds()),
                )
            )
        # Flushed first: the details reference the registry rows.
        self._session.flush()
        self._session.add_all(details)

    def _delete_where(self, *conditions) -> int:
        ids = list(
            self._session.exec(
                select(CredentialRecordTable.id).where(CredentialRecordTable.kind == CredentialKind.TOKEN, *conditions)
            ).all()
        )
        if not ids:
            return 0
        # Both deleted explicitly, details first: the cascade does not run where
        # foreign keys are not enforced.
        self._session.exec(  # type: ignore[call-overload]
            delete(TokenCredentialRecordTable).where(TokenCredentialRecordTable.credential_id.in_(ids))  # type: ignore[attr-defined]
        )
        self._session.exec(delete(CredentialRecordTable).where(CredentialRecordTable.id.in_(ids)))  # type: ignore[call-overload,attr-defined]
        return len(ids)

    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        self._add(credential_records)
        self.commit()

    @override
    def create_within_limit(self, credential_record: TokenCredentialRecord, limit: int, now: datetime) -> bool:
        # The principal's row is locked first, for the rest of the transaction:
        # a second issuance for the same principal waits for this one to commit,
        # then counts it. SQLite has no row locks and renders the clause away,
        # which is fine, its single writer already serialises the two.
        self._session.exec(
            select(PrincipalTable.id).where(PrincipalTable.id == credential_record.principal_id).with_for_update()
        )
        held = self._find_all(CredentialRecordTable.principal_id == credential_record.principal_id)
        if sum(record.is_usable(now) for record in held) >= limit:
            self._session.rollback()
            return False
        self._add((credential_record,))
        self.commit()
        return True

    @override
    def replace_token_hashes(self, token_hashes: Iterable[str], new_token_hashes: Iterable[str]) -> None:
        new_token_hash_by_old = dict(zip(token_hashes, new_token_hashes, strict=True))
        result = self._session.exec(  # type: ignore[call-overload]
            update(TokenCredentialRecordTable)
            .where(TokenCredentialRecordTable.token_hash.in_(list(new_token_hash_by_old)))  # type: ignore[attr-defined]
            .values(token_hash=case(new_token_hash_by_old, value=TokenCredentialRecordTable.token_hash))
        )

        # Make sur all updates were done
        if result.rowcount != len(new_token_hash_by_old):
            self._session.rollback()
            raise CannotRotateTokenCredentialError()

        self.commit()

    @override
    def list_by_principal_ids(self, principal_ids: Iterable[UUID]) -> list[TokenCredentialRecord]:
        return self._find_all(CredentialRecordTable.principal_id.in_(list(principal_ids)))  # type: ignore[attr-defined]

    @override
    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        records = self._find_all(TokenCredentialRecordTable.token_hash == token_hash)
        return records[0] if records else None

    @override
    def get_by_id(self, credential_id: UUID) -> TokenCredentialRecord | None:
        records = self._find_all(CredentialRecordTable.id == credential_id)
        return records[0] if records else None

    @override
    def delete(self, credential_ids: Iterable[UUID]) -> int:
        deleted = self._delete_where(CredentialRecordTable.id.in_(list(credential_ids)))  # type: ignore[attr-defined]
        self.commit()
        return deleted

    @override
    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> int:
        deleted = self._delete_where(CredentialRecordTable.principal_id.in_(list(principal_ids)))  # type: ignore[attr-defined]
        self.commit()
        return deleted

    @override
    def touch_last_used(self, credential_id: UUID, now: datetime, coarsening: timedelta) -> None:
        # One conditional UPDATE: no read first, and no write at all while the
        # stored value is recent enough.
        naive_now = to_naive_utc(now)
        self._session.exec(  # type: ignore[call-overload]
            update(TokenCredentialRecordTable)
            .where(
                TokenCredentialRecordTable.credential_id == credential_id,
                or_(
                    TokenCredentialRecordTable.last_used_at.is_(None),  # type: ignore[union-attr]
                    TokenCredentialRecordTable.last_used_at <= naive_now - coarsening,  # type: ignore[operator]
                ),
            )
            .values(last_used_at=naive_now)
        )
        self.commit()

from collections.abc import Iterable
from typing import override
from uuid import UUID, uuid4

from sqlalchemy import case
from sqlmodel import Session, delete, select, update

from identity_access_management_context.application.gateways import (
    CannotRotateTokenCredentialError,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.domain.entities import TokenCredentialRecord
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.credential_record import CredentialKind, CredentialRecordTable, TokenCredentialRecordTable


class SqlTokenCredentialRecordRepository(SQLBaseRepository, TokenCredentialRecordRepository):
    """Token credential records, stored as a credential registry row plus the token hash."""

    def __init__(self, session: Session):
        super().__init__(session)

    def _add(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        details = []
        for credential_record in credential_records:
            credential_id = uuid4()
            self._session.add(
                CredentialRecordTable(
                    id=credential_id,
                    kind=CredentialKind.TOKEN,
                    principal_id=credential_record.principal_id,
                )
            )
            details.append(
                TokenCredentialRecordTable(credential_id=credential_id, token_hash=credential_record.token_hash)
            )
        # Flushed first: the details reference the registry rows.
        self._session.flush()
        self._session.add_all(details)

    def _delete(self, principal_ids: Iterable[UUID]) -> None:
        holds_token = (
            CredentialRecordTable.principal_id.in_(list(principal_ids)),  # type: ignore[attr-defined]
            CredentialRecordTable.kind == CredentialKind.TOKEN,
        )
        # Both deleted explicitly, details first: the cascade does not run where
        # foreign keys are not enforced.
        self._session.exec(  # type: ignore[call-overload]
            delete(TokenCredentialRecordTable).where(
                TokenCredentialRecordTable.credential_id.in_(  # type: ignore[attr-defined]
                    select(CredentialRecordTable.id).where(*holds_token)
                )
            )
        )
        self._session.exec(delete(CredentialRecordTable).where(*holds_token))  # type: ignore[call-overload]

    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        self._add(credential_records)
        self.commit()

    @override
    def _replace(self, token_hashes: Iterable[str], new_token_hashes: Iterable[str]) -> None:
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
        statement = (
            select(CredentialRecordTable.principal_id, TokenCredentialRecordTable.token_hash)
            .join(
                CredentialRecordTable,
                TokenCredentialRecordTable.credential_id == CredentialRecordTable.id,  # pyright: ignore[reportArgumentType]
            )
            .where(CredentialRecordTable.principal_id.in_(list(principal_ids)))  # type: ignore[attr-defined]
        )
        return [
            TokenCredentialRecord(principal_id=principal_id, token_hash=token_hash)
            for principal_id, token_hash in self._session.exec(statement).all()
        ]

    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        statement = (
            select(CredentialRecordTable.principal_id, TokenCredentialRecordTable.token_hash)
            .join(
                CredentialRecordTable,
                TokenCredentialRecordTable.credential_id == CredentialRecordTable.id,  # pyright: ignore[reportArgumentType]
            )
            .where(TokenCredentialRecordTable.token_hash == token_hash)
        )
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return TokenCredentialRecord(principal_id=row[0], token_hash=row[1])

    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> None:
        self._delete(principal_ids)
        self.commit()

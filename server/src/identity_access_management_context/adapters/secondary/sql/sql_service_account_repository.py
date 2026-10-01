from collections.abc import Iterable, Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import case
from sqlmodel import Session, select, update

from identity_access_management_context.adapters.secondary.sql.model.principal_model import (
    PrincipalKind,
    PrincipalTable,
)
from identity_access_management_context.adapters.secondary.sql.model.service_account_model import (
    ServiceAccountPrincipalTable,
)
from identity_access_management_context.application.gateways import (
    CannotRevokeServiceAccount,
    CannotRotateServiceAccount,
    ServiceAccountRepository,
)
from identity_access_management_context.domain.entities import ServiceAccount
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import to_naive_utc
from shared_kernel.utils.naive_utc import as_utc


class SqlServiceAccountRepository(SQLBaseRepository, ServiceAccountRepository):
    """Service accounts, stored as a principal registry row plus their account details."""

    def __init__(self, session: Session):
        super().__init__(session)

    @staticmethod
    def _to_entity(row: ServiceAccountPrincipalTable) -> ServiceAccount:
        """Map the persistence row onto the domain entity."""
        return ServiceAccount(
            id=row.principal_id,
            group_id=row.group_id,
            name=row.name,
            token_hash=row.token_hash,
            revoked_at=as_utc(row.revoked_at),
        )

    def create(self, accounts: Iterable[ServiceAccount]) -> None:
        accounts = list(accounts)
        # The registry rows and the details are the same principals: committed together.
        self._session.add_all(PrincipalTable(id=account.id, kind=PrincipalKind.SERVICE_ACCOUNT) for account in accounts)
        rows = [
            ServiceAccountPrincipalTable(
                principal_id=account.id,
                group_id=account.group_id,
                name=account.name,
                token_hash=account.token_hash,
                revoked_at=to_naive_utc(account.revoked_at),
            )
            for account in accounts
        ]
        self._session.add_all(rows)
        self.commit()

    def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[ServiceAccount | None]:
        query = select(ServiceAccountPrincipalTable).where(ServiceAccountPrincipalTable.principal_id.in_(ids))  # type: ignore[attr-defined]
        rows = self._session.exec(query).all()
        accounts_by_id = {row.principal_id: self._to_entity(row) for row in rows}

        # One slot per requested id, empty where there is no such account.
        return [accounts_by_id.get(account_id) for account_id in ids]

    def get_by_token_hash(self, token_hash: str) -> ServiceAccount | None:
        query = select(ServiceAccountPrincipalTable).where(ServiceAccountPrincipalTable.token_hash == token_hash)
        row = self._session.exec(query).first()
        return self._to_entity(row) if row is not None else None

    def list_for_groups(self, group_ids: Sequence[UUID]) -> Iterable[ServiceAccount]:
        query = select(ServiceAccountPrincipalTable).where(ServiceAccountPrincipalTable.group_id.in_(group_ids))  # type: ignore[attr-defined]
        rows = self._session.exec(query).all()
        return [self._to_entity(row) for row in rows]

    def rotate(self, ids: Sequence[UUID], hashes: Sequence[str]) -> None:
        new_hashes = dict(zip(ids, hashes, strict=True))

        # One statement for the batch: CASE picks each account's own hash.
        statement = (
            update(ServiceAccountPrincipalTable)
            .where(
                ServiceAccountPrincipalTable.principal_id.in_(new_hashes),  # type: ignore[attr-defined]
                ServiceAccountPrincipalTable.revoked_at.is_(None),  # type: ignore[union-attr]
            )
            .values(token_hash=case(new_hashes, value=ServiceAccountPrincipalTable.principal_id))
        )
        result = self._session.exec(statement)  # type: ignore[call-overload]

        # Fewer rows written than asked for means at least one was revoked.
        if result.rowcount != len(new_hashes):
            self._session.rollback()
            raise CannotRotateServiceAccount(self._first_inactive(list(new_hashes)))

        self.commit()

    def revoke(self, ids: Iterable[UUID], now: datetime) -> None:
        account_ids = list(ids)

        statement = (
            update(ServiceAccountPrincipalTable)
            .where(
                ServiceAccountPrincipalTable.principal_id.in_(account_ids),  # type: ignore[attr-defined]
                ServiceAccountPrincipalTable.revoked_at.is_(None),  # type: ignore[union-attr]
            )
            .values(revoked_at=to_naive_utc(now))
        )
        result = self._session.exec(statement)  # type: ignore[call-overload]

        # Refusing the batch whole keeps an earlier revocation's timestamp intact.
        if result.rowcount != len(account_ids):
            self._session.rollback()
            raise CannotRevokeServiceAccount(self._first_inactive(account_ids))

        self.commit()

    def _first_inactive(self, ids: Sequence[UUID]) -> UUID:
        """Return the first of these ids that is revoked or absent."""
        query = select(ServiceAccountPrincipalTable.principal_id).where(
            ServiceAccountPrincipalTable.principal_id.in_(ids),  # type: ignore[attr-defined]
            ServiceAccountPrincipalTable.revoked_at.is_(None),  # type: ignore[union-attr]
        )
        active_ids = set(self._session.exec(query).all())
        return next(account_id for account_id in ids if account_id not in active_ids)

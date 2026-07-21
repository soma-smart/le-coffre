from datetime import UTC, datetime
from typing import overload
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select, update

from password_management_context.adapters.secondary.sql.model.one_time_link import (
    OneTimeLinkTable,
)
from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.domain.entities import OneTimeLink
from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository


def _as_utc(value: datetime | None) -> datetime | None:
    """Re-attach UTC to a timestamp coming back from the database.

    The column type is naive, so a reloaded row yields naive datetimes while
    TimeGateway hands the domain aware ones. Comparing the two raises TypeError,
    which would blow up expiry checks on any link not still in the session's
    identity map. Everything written here is UTC, so re-attaching it is sound.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


@overload
def _to_naive_utc(value: datetime) -> datetime: ...


@overload
def _to_naive_utc(value: None) -> None: ...


def _to_naive_utc(value: datetime | None) -> datetime | None:
    """Convert to UTC then drop the tzinfo, matching how the column stores it.

    Applied at every write and every comparison. Without it the driver decides
    what to do with an aware value, and SQLite keeps the local wall clock while
    discarding the offset: an instant of 11:00+02:00 lands as 11:00, two hours
    off. Expiry is then compared against a correctly normalised `now`, so a link
    would outlive its lifetime by the size of the offset.
    """
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_entity(row: OneTimeLinkTable) -> OneTimeLink:
    """Map the persistence row onto the domain entity.

    Explicit rather than returning the ORM object, so callers never end up
    holding a live session-bound row behind a domain-typed signature.
    """
    return OneTimeLink(
        id=row.id,
        password_id=row.password_id,
        token_hash=row.token_hash,
        created_by_user_id=row.created_by_user_id,
        created_at=_as_utc(row.created_at),  # type: ignore[arg-type]
        expires_at=_as_utc(row.expires_at),  # type: ignore[arg-type]
        read_at=_as_utc(row.read_at),
        revoked_at=_as_utc(row.revoked_at),
    )


class SqlOneTimeLinkRepository(SQLBaseRepository, OneTimeLinkRepository):
    """SQL implementation of the one-time link repository"""

    def __init__(self, session: Session):
        super().__init__(session)

    def add(self, link: OneTimeLink) -> None:
        row = OneTimeLinkTable(
            id=link.id,
            password_id=link.password_id,
            token_hash=link.token_hash,
            created_by_user_id=link.created_by_user_id,
            created_at=_to_naive_utc(link.created_at),
            expires_at=_to_naive_utc(link.expires_at),
            read_at=_to_naive_utc(link.read_at),
            revoked_at=_to_naive_utc(link.revoked_at),
        )
        self._session.add(row)
        self.commit()

    def get_by_id(self, link_id: UUID) -> OneTimeLink | None:
        row = self._session.get(OneTimeLinkTable, link_id)
        return _to_entity(row) if row else None

    def get_by_token_hash(self, token_hash: str) -> OneTimeLink | None:
        row = self._session.exec(select(OneTimeLinkTable).where(OneTimeLinkTable.token_hash == token_hash)).first()
        return _to_entity(row) if row else None

    def list_for_password(self, password_id: UUID, limit: int) -> list[OneTimeLink]:
        query = (
            select(OneTimeLinkTable)
            .where(OneTimeLinkTable.password_id == password_id)
            .order_by(OneTimeLinkTable.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return [_to_entity(row) for row in self._session.exec(query).all()]

    def list_active_for_password(self, password_id: UUID, now: datetime, limit: int) -> list[OneTimeLink]:
        query = (
            select(OneTimeLinkTable)
            .where(
                OneTimeLinkTable.password_id == password_id,
                OneTimeLinkTable.read_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.revoked_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.expires_at > _to_naive_utc(now),
            )
            .order_by(OneTimeLinkTable.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return [_to_entity(row) for row in self._session.exec(query).all()]

    def count_for_password(self, password_id: UUID) -> int:
        statement = (
            select(func.count()).select_from(OneTimeLinkTable).where(OneTimeLinkTable.password_id == password_id)
        )
        return self._session.exec(statement).one()  # type: ignore[call-overload]

    def count_active_for_password(self, password_id: UUID, now: datetime) -> int:
        # Counted in SQL rather than by loading and filtering rows: this runs on
        # every link creation, and the row set is unbounded over a password's life.
        #
        # The column is naive UTC, so the bound value is stripped to naive UTC
        # explicitly. Drivers do that truncation for us today, but relying on it
        # would make the comparison silently driver-dependent, and a comparison
        # that skews here under-counts active links and lets the cap be exceeded.
        statement = (
            select(func.count())
            .select_from(OneTimeLinkTable)
            .where(
                OneTimeLinkTable.password_id == password_id,
                OneTimeLinkTable.read_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.revoked_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.expires_at > _to_naive_utc(now),
            )
        )
        return self._session.exec(statement).one()  # type: ignore[call-overload]

    def count_all(self) -> int:
        return self._session.exec(select(func.count()).select_from(OneTimeLinkTable)).one()  # type: ignore[call-overload]

    def count_active_all(self, now: datetime) -> int:
        statement = (
            select(func.count())
            .select_from(OneTimeLinkTable)
            .where(
                OneTimeLinkTable.read_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.revoked_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.expires_at > _to_naive_utc(now),
            )
        )
        return self._session.exec(statement).one()  # type: ignore[call-overload]

    def consume(self, link_id: UUID, now: datetime) -> bool:
        # One conditional UPDATE, not a read-then-write. The WHERE clause is the
        # concurrency guard: whichever transaction gets rowcount 1 is the single
        # reader, everyone else gets 0 and is told the link is already used.
        statement = (
            update(OneTimeLinkTable)
            .where(
                OneTimeLinkTable.id == link_id,  # type: ignore[arg-type]
                OneTimeLinkTable.read_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.revoked_at.is_(None),  # type: ignore[union-attr]
            )
            .values(read_at=_to_naive_utc(now))
        )
        result = self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()
        return result.rowcount == 1

    def revoke(self, link_id: UUID, now: datetime) -> bool:
        # Same guard as consume: a revoke must never land on a link that was
        # already read, or it would erase the read timestamp from the audit trail.
        statement = (
            update(OneTimeLinkTable)
            .where(
                OneTimeLinkTable.id == link_id,  # type: ignore[arg-type]
                OneTimeLinkTable.read_at.is_(None),  # type: ignore[union-attr]
                OneTimeLinkTable.revoked_at.is_(None),  # type: ignore[union-attr]
            )
            .values(revoked_at=_to_naive_utc(now))
        )
        result = self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()
        return result.rowcount == 1

    def delete_for_password(self, password_id: UUID) -> None:
        rows = self._session.exec(select(OneTimeLinkTable).where(OneTimeLinkTable.password_id == password_id)).all()
        for row in rows:
            self._session.delete(row)
        self.commit()

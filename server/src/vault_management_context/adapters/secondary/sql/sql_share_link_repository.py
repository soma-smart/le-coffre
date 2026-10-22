from datetime import datetime
from uuid import UUID

from sqlmodel import Session, delete, or_, select, update

from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc
from vault_management_context.application.gateways import ShareLinkRepository
from vault_management_context.domain.entities import ShareLink
from vault_management_context.domain.value_objects import ShareLinkDelivery

from .models.vault_share_link import VaultShareLinkTable


def _to_entity(row: VaultShareLinkTable) -> ShareLink:
    return ShareLink(
        id=row.id,
        setup_id=row.setup_id,
        share_index=row.share_index,
        lookup_hash=row.lookup_hash,
        ack_hash=row.ack_hash,
        sealed_share=row.sealed_share,
        created_at=as_utc(row.created_at),  # type: ignore[arg-type]
        expires_at=as_utc(row.expires_at),  # type: ignore[arg-type]
        delivered_at=as_utc(row.delivered_at),
        reopenable_until=as_utc(row.reopenable_until),
    )


class SqlShareLinkRepository(SQLBaseRepository, ShareLinkRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def replace_all(self, links: list[ShareLink]) -> None:
        self._session.exec(delete(VaultShareLinkTable))  # type: ignore[call-overload]
        for link in links:
            self._session.add(
                VaultShareLinkTable(
                    id=link.id,
                    setup_id=link.setup_id,
                    share_index=link.share_index,
                    lookup_hash=link.lookup_hash,
                    ack_hash=link.ack_hash,
                    sealed_share=link.sealed_share,
                    created_at=to_naive_utc(link.created_at),
                    expires_at=to_naive_utc(link.expires_at),
                    delivered_at=to_naive_utc(link.delivered_at),
                    reopenable_until=to_naive_utc(link.reopenable_until),
                )
            )
        self.commit()

    def get_by_lookup_hash(self, lookup_hash: str) -> ShareLink | None:
        row = self._session.exec(
            select(VaultShareLinkTable).where(VaultShareLinkTable.lookup_hash == lookup_hash)
        ).first()
        return _to_entity(row) if row else None

    def deliver(self, link_id: UUID, now: datetime, reopenable_until: datetime) -> ShareLinkDelivery | None:
        naive_now = to_naive_utc(now)
        # First delivery: one conditional UPDATE, so two concurrent first
        # openings cannot both start the window; the loser falls through to the
        # reopening branch below.
        first = self._session.exec(
            update(VaultShareLinkTable)  # type: ignore[call-overload]
            .where(
                VaultShareLinkTable.id == link_id,  # type: ignore[arg-type]
                VaultShareLinkTable.delivered_at.is_(None),  # type: ignore[union-attr]
                VaultShareLinkTable.expires_at > naive_now,  # type: ignore[arg-type]
            )
            .values(delivered_at=naive_now, reopenable_until=to_naive_utc(reopenable_until))
        )
        self.commit()
        if first.rowcount == 1:
            return ShareLinkDelivery(first_delivered_at=now, reopenable_until=reopenable_until, reopened=False)

        # populate_existing: should the row still sit in the session from an
        # earlier read, its values predate the concurrent first delivery.
        row = self._session.exec(
            select(VaultShareLinkTable)
            .where(
                VaultShareLinkTable.id == link_id,
                VaultShareLinkTable.expires_at > naive_now,  # type: ignore[arg-type]
                VaultShareLinkTable.reopenable_until > naive_now,  # type: ignore[arg-type,operator]
            )
            .execution_options(populate_existing=True)
        ).first()
        if row is None:
            return None
        return ShareLinkDelivery(
            first_delivered_at=as_utc(row.delivered_at),  # type: ignore[arg-type]
            reopenable_until=as_utc(row.reopenable_until),  # type: ignore[arg-type]
            reopened=True,
        )

    def remove_delivered(self, link_id: UUID, now: datetime) -> bool:
        naive_now = to_naive_utc(now)
        statement = delete(VaultShareLinkTable).where(
            VaultShareLinkTable.id == link_id,  # type: ignore[arg-type]
            VaultShareLinkTable.delivered_at.is_not(None),  # type: ignore[union-attr]
            VaultShareLinkTable.reopenable_until > naive_now,  # type: ignore[arg-type,operator]
            VaultShareLinkTable.expires_at > naive_now,  # type: ignore[arg-type]
        )
        result = self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()
        return result.rowcount == 1

    def purge_expired(self, now: datetime) -> None:
        naive_now = to_naive_utc(now)
        statement = delete(VaultShareLinkTable).where(
            or_(
                VaultShareLinkTable.expires_at <= naive_now,  # type: ignore[arg-type]
                VaultShareLinkTable.reopenable_until <= naive_now,  # type: ignore[arg-type,operator]
            )
        )
        self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()

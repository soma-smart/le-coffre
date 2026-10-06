from datetime import datetime
from uuid import UUID

from sqlmodel import Session, delete, select

from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc
from vault_management_context.application.gateways import ShareLinkRepository
from vault_management_context.domain.entities import ShareLink

from .models.vault_share_link import VaultShareLinkTable


def _to_entity(row: VaultShareLinkTable) -> ShareLink:
    return ShareLink(
        id=row.id,
        setup_id=row.setup_id,
        share_index=row.share_index,
        lookup_hash=row.lookup_hash,
        sealed_share=row.sealed_share,
        created_at=as_utc(row.created_at),  # type: ignore[arg-type]
        expires_at=as_utc(row.expires_at),  # type: ignore[arg-type]
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
                    sealed_share=link.sealed_share,
                    created_at=to_naive_utc(link.created_at),
                    expires_at=to_naive_utc(link.expires_at),
                )
            )
        self.commit()

    def get_by_lookup_hash(self, lookup_hash: str) -> ShareLink | None:
        row = self._session.exec(
            select(VaultShareLinkTable).where(VaultShareLinkTable.lookup_hash == lookup_hash)
        ).first()
        return _to_entity(row) if row else None

    def consume(self, link_id: UUID, now: datetime) -> bool:
        # One conditional DELETE, not a read-then-write: the WHERE clause is the
        # concurrency guard, so only one caller ever gets rowcount 1.
        statement = delete(VaultShareLinkTable).where(
            VaultShareLinkTable.id == link_id,  # type: ignore[arg-type]
            VaultShareLinkTable.expires_at > to_naive_utc(now),  # type: ignore[arg-type]
        )
        result = self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()
        return result.rowcount == 1

    def purge_expired(self, now: datetime) -> None:
        statement = delete(VaultShareLinkTable).where(
            VaultShareLinkTable.expires_at <= to_naive_utc(now),  # type: ignore[arg-type]
        )
        self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()

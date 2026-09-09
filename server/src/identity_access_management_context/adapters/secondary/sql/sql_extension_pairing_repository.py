from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, delete, select, update

from identity_access_management_context.adapters.secondary.sql.model.extension_pairing_model import (
    ExtensionPairingTable,
)
from identity_access_management_context.application.gateways import ExtensionPairingRepository
from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.value_objects import PairingUserCode, PkceChallenge
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc


class SqlExtensionPairingRepository(SQLBaseRepository, ExtensionPairingRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def add(self, pairing: ExtensionPairing) -> ExtensionPairing:
        db_obj = ExtensionPairingTable(
            id=pairing.id,
            user_code=pairing.user_code.value,
            code_challenge=pairing.code_challenge.value,
            device_name=pairing.device_name,
            created_at=to_naive_utc(pairing.created_at),
            expires_at=to_naive_utc(pairing.expires_at),
            approved_at=to_naive_utc(pairing.approved_at),
            approved_by_user_id=pairing.approved_by_user_id,
            denied_at=to_naive_utc(pairing.denied_at),
            consumed_at=to_naive_utc(pairing.consumed_at),
            created_from_ip=pairing.created_from_ip,
        )
        self._session.add(db_obj)
        self.commit_and_refresh(db_obj)
        return self._to_entity(db_obj)

    def get_by_user_code(self, user_code: PairingUserCode) -> ExtensionPairing | None:
        statement = select(ExtensionPairingTable).where(ExtensionPairingTable.user_code == user_code.value)
        row = self._session.exec(statement).first()
        return self._to_entity(row) if row is not None else None

    def save(self, pairing: ExtensionPairing) -> None:
        statement = select(ExtensionPairingTable).where(ExtensionPairingTable.id == pairing.id)
        row = self._session.exec(statement).first()
        if row is None:
            return

        row.approved_at = to_naive_utc(pairing.approved_at)
        row.approved_by_user_id = pairing.approved_by_user_id
        row.denied_at = to_naive_utc(pairing.denied_at)
        row.consumed_at = to_naive_utc(pairing.consumed_at)
        self._session.add(row)
        self.commit_and_refresh(row)

    def consume(self, pairing_id: UUID, now: datetime) -> bool:
        # One conditional UPDATE, not a read-then-write. The WHERE clause is the
        # concurrency guard: whichever transaction gets rowcount 1 is the single
        # redeemer, so two simultaneous exchanges cannot both mint a credential.
        statement = (
            update(ExtensionPairingTable)
            .where(
                cast(Any, ExtensionPairingTable.id) == pairing_id,
                cast(Any, ExtensionPairingTable.consumed_at).is_(None),
                cast(Any, ExtensionPairingTable.denied_at).is_(None),
                cast(Any, ExtensionPairingTable.approved_at).is_not(None),
            )
            .values(consumed_at=to_naive_utc(now))
        )
        result = self._session.exec(cast(Any, statement))
        self.commit()
        return cast(Any, result).rowcount == 1

    def purge_expired(self, cutoff: datetime) -> None:
        self._session.exec(
            cast(
                Any,
                delete(ExtensionPairingTable).where(cast(Any, ExtensionPairingTable.expires_at) < to_naive_utc(cutoff)),
            )
        )
        self.commit()

    def _to_entity(self, table: ExtensionPairingTable) -> ExtensionPairing:
        return ExtensionPairing(
            id=table.id,
            user_code=PairingUserCode(value=table.user_code),
            code_challenge=PkceChallenge(value=table.code_challenge),
            device_name=table.device_name,
            created_at=as_utc(table.created_at),
            expires_at=as_utc(table.expires_at),
            approved_at=as_utc(table.approved_at),
            approved_by_user_id=table.approved_by_user_id,
            denied_at=as_utc(table.denied_at),
            consumed_at=as_utc(table.consumed_at),
            created_from_ip=table.created_from_ip,
        )

from collections.abc import Iterable
from uuid import uuid4

from sqlmodel import Session, select

from identity_access_management_context.application.gateways import ServiceAccountTokenCredentialRecordRepository
from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.credential_model import CredentialKind, CredentialRecordTable
from .model.service_account_token_credential_model import ServiceAccountTokenCredentialRecordTable


class SqlServiceAccountTokenCredentialRecordRepository(
    SQLBaseRepository, ServiceAccountTokenCredentialRecordRepository
):
    """Token credential records, stored as a credential registry row plus the token hash."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        details = []
        for credential_record in credential_records:
            credential_id = uuid4()
            self._session.add(
                CredentialRecordTable(
                    id=credential_id,
                    kind=CredentialKind.SERVICE_ACCOUNT_TOKEN,
                    principal_id=credential_record.principal_id,
                )
            )
            details.append(
                ServiceAccountTokenCredentialRecordTable(
                    credential_id=credential_id, token_hash=credential_record.token_hash
                )
            )
        # Flushed first: the details reference the registry rows.
        self._session.flush()
        self._session.add_all(details)
        self.commit()

    def replace(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        for credential_record in credential_records:
            # Every account gets its credential at creation, so there is always one to replace.
            statement = (
                select(ServiceAccountTokenCredentialRecordTable)
                .join(
                    CredentialRecordTable,
                    ServiceAccountTokenCredentialRecordTable.credential_id == CredentialRecordTable.id,
                )
                .where(CredentialRecordTable.principal_id == credential_record.principal_id)
            )
            details = self._session.exec(statement).one()
            details.token_hash = credential_record.token_hash
            self._session.add(details)
        self.commit()

    def get_by_token_hash(self, token_hash: str) -> ServiceAccountTokenCredentialRecord | None:
        statement = (
            select(CredentialRecordTable.principal_id, ServiceAccountTokenCredentialRecordTable.token_hash)
            .join(
                CredentialRecordTable,
                ServiceAccountTokenCredentialRecordTable.credential_id == CredentialRecordTable.id,
            )
            .where(ServiceAccountTokenCredentialRecordTable.token_hash == token_hash)
        )
        row = self._session.exec(statement).first()
        if row is None:
            return None
        return ServiceAccountTokenCredentialRecord(principal_id=row[0], token_hash=row[1])

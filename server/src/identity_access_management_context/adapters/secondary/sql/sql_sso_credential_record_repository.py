from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Session, select

from identity_access_management_context.domain.entities import SSOCredentialRecord
from identity_access_management_context.domain.exceptions import (
    SSOCredentialAlreadyExistsException,
)
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.credential_model import CredentialKind, CredentialRecordTable
from .model.sso_credential_model import SSOCredentialRecordTable


class SqlSSOCredentialRecordRepository(SQLBaseRepository):
    """SSO credential records, stored as a credential registry row plus the provider's subject."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(self, credential_record: SSOCredentialRecord) -> None:
        if self._find_by_subject(credential_record.provider, credential_record.subject) is not None:
            raise SSOCredentialAlreadyExistsException(
                f"SSO subject {credential_record.subject} with provider {credential_record.provider} already exists"
            )

        credential_id = uuid4()
        self._session.add(
            CredentialRecordTable(
                id=credential_id, kind=CredentialKind.SSO, principal_id=credential_record.principal_id
            )
        )
        # Flushed first: the details reference the registry row.
        self._session.flush()
        # Unset timestamps are left to the column defaults.
        timestamps = {
            name: value
            for name, value in (
                ("created_at", credential_record.created_at),
                ("last_login", credential_record.last_login),
            )
            if value is not None
        }
        self._session.add(
            SSOCredentialRecordTable(
                credential_id=credential_id,
                provider=credential_record.provider,
                subject=credential_record.subject,
                **timestamps,
            )
        )
        self.commit()

    def update_last_login(self, provider: str, subject: str, last_login: datetime) -> None:
        found = self._find_by_subject(provider, subject)
        if found is not None:
            _, details = found
            details.last_login = last_login
            self._session.add(details)
            self.commit()

    def get_by_subject(self, provider: str, subject: str) -> SSOCredentialRecord | None:
        found = self._find_by_subject(provider, subject)
        return self._to_entity(*found) if found else None

    def get_by_principal_id(self, principal_id: UUID) -> SSOCredentialRecord | None:
        found = self._find(CredentialRecordTable.principal_id == principal_id)
        return self._to_entity(*found) if found else None

    def _find_by_subject(
        self, provider: str, subject: str
    ) -> tuple[CredentialRecordTable, SSOCredentialRecordTable] | None:
        return self._find(SSOCredentialRecordTable.provider == provider, SSOCredentialRecordTable.subject == subject)

    def _find(self, *conditions) -> tuple[CredentialRecordTable, SSOCredentialRecordTable] | None:
        statement = (
            select(CredentialRecordTable, SSOCredentialRecordTable)
            .join(SSOCredentialRecordTable, SSOCredentialRecordTable.credential_id == CredentialRecordTable.id)
            .where(*conditions)
        )
        row = self._session.exec(statement).first()
        return (row[0], row[1]) if row else None

    @staticmethod
    def _to_entity(registry: CredentialRecordTable, details: SSOCredentialRecordTable) -> SSOCredentialRecord:
        return SSOCredentialRecord(
            principal_id=registry.principal_id,
            provider=details.provider,
            subject=details.subject,
            created_at=details.created_at,
            last_login=details.last_login,
        )

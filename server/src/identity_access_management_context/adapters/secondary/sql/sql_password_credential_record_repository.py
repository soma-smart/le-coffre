from uuid import UUID, uuid4

from sqlmodel import Session, select

from identity_access_management_context.domain.entities import PasswordCredentialRecord
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.credential_model import CredentialKind, CredentialRecordTable
from .model.password_credential_model import PasswordCredentialRecordTable


class SqlPasswordCredentialRecordRepository(SQLBaseRepository):
    """Password credential records, stored as a credential registry row plus the password details."""

    def __init__(self, session: Session):
        super().__init__(session)

    def save(self, credential_record: PasswordCredentialRecord) -> None:
        credential_id = uuid4()
        self._session.add(
            CredentialRecordTable(
                id=credential_id, kind=CredentialKind.PASSWORD, principal_id=credential_record.principal_id
            )
        )
        # Flushed first: the details reference the registry row.
        self._session.flush()
        self._session.add(
            PasswordCredentialRecordTable(
                credential_id=credential_id,
                email=credential_record.email,
                password_hash=credential_record.password_hash,
            )
        )
        self.commit()

    def delete_by_principal_id(self, principal_id: UUID) -> None:
        found = self._find(CredentialRecordTable.principal_id == principal_id)
        if found is None:
            return
        registry, details = found
        # Both deleted explicitly, details first: the cascade does not run where
        # foreign keys are not enforced.
        self._session.delete(details)
        self._session.flush()
        self._session.delete(registry)
        self.commit()

    def update_password_hash(self, principal_id: UUID, new_password_hash: bytes) -> None:
        found = self._find(CredentialRecordTable.principal_id == principal_id)
        if found is None:
            return
        _, details = found
        details.password_hash = new_password_hash
        self._session.add(details)
        self.commit()

    def get_by_principal_id(self, principal_id: UUID) -> PasswordCredentialRecord | None:
        found = self._find(CredentialRecordTable.principal_id == principal_id)
        return self._to_entity(*found) if found else None

    def get_by_email(self, email: str) -> PasswordCredentialRecord | None:
        found = self._find(PasswordCredentialRecordTable.email == email)
        return self._to_entity(*found) if found else None

    def _find(self, condition) -> tuple[CredentialRecordTable, PasswordCredentialRecordTable] | None:
        statement = (
            select(CredentialRecordTable, PasswordCredentialRecordTable)
            .join(
                PasswordCredentialRecordTable, PasswordCredentialRecordTable.credential_id == CredentialRecordTable.id
            )
            .where(condition)
        )
        row = self._session.exec(statement).first()
        return (row[0], row[1]) if row else None

    @staticmethod
    def _to_entity(registry: CredentialRecordTable, details: PasswordCredentialRecordTable) -> PasswordCredentialRecord:
        return PasswordCredentialRecord(
            principal_id=registry.principal_id, email=details.email, password_hash=details.password_hash
        )

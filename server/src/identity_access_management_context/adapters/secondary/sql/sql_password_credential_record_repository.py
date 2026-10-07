from uuid import UUID, uuid4

from sqlmodel import Session, select

from identity_access_management_context.domain.entities import PasswordCredentialRecord
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.credential_record import CredentialKind, CredentialRecordTable, PasswordCredentialRecordTable


class SqlPasswordCredentialRecordRepository(SQLBaseRepository):
    """Password credential records, stored as a credential registry row plus the password details."""

    def __init__(self, session: Session):
        super().__init__(session)

    @staticmethod
    def _to_entity(registry: CredentialRecordTable, details: PasswordCredentialRecordTable) -> PasswordCredentialRecord:
        return PasswordCredentialRecord(
            principal_id=registry.principal_id, email=details.email, password_hash=details.password_hash
        )

    def _find_all(self, condition) -> list[tuple[CredentialRecordTable, PasswordCredentialRecordTable]]:
        statement = (
            select(CredentialRecordTable, PasswordCredentialRecordTable)
            .join(
                PasswordCredentialRecordTable, PasswordCredentialRecordTable.credential_id == CredentialRecordTable.id
            )
            .where(condition)
        )
        return [(row[0], row[1]) for row in self._session.exec(statement).all()]

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

    def update_password_hash(self, email: str, new_password_hash: bytes) -> None:
        for _, details in self._find_all(PasswordCredentialRecordTable.email == email):
            details.password_hash = new_password_hash
            self._session.add(details)
        self.commit()

    def list_by_principal_id(self, principal_id: UUID) -> list[PasswordCredentialRecord]:
        return [self._to_entity(*found) for found in self._find_all(CredentialRecordTable.principal_id == principal_id)]

    def get_by_email(self, email: str) -> PasswordCredentialRecord | None:
        found = self._find_all(PasswordCredentialRecordTable.email == email)
        return self._to_entity(*found[0]) if found else None

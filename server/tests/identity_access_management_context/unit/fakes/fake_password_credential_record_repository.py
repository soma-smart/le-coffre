from uuid import UUID

from identity_access_management_context.domain.entities import PasswordCredentialRecord


class FakePasswordCredentialRecordRepository:
    def __init__(self):
        self._credential_records: dict[UUID, PasswordCredentialRecord] = {}

    def save(self, credential_record: PasswordCredentialRecord) -> None:
        self._credential_records[credential_record.principal_id] = credential_record

    def update_password_hash(self, principal_id: UUID, new_password_hash: bytes) -> None:
        if principal_id in self._credential_records:
            self._credential_records[principal_id].password_hash = new_password_hash

    def get_by_principal_id(self, principal_id: UUID) -> PasswordCredentialRecord | None:
        return self._credential_records.get(principal_id)

    def get_by_email(self, email: str) -> PasswordCredentialRecord | None:
        return next((c for c in self._credential_records.values() if c.email == email), None)

    def delete_by_principal_id(self, principal_id: UUID) -> None:
        self._credential_records.pop(principal_id, None)

from uuid import UUID

from identity_access_management_context.domain.entities import PasswordCredentialRecord


class FakePasswordCredentialRecordRepository:
    def __init__(self):
        self._credential_records: list[PasswordCredentialRecord] = []

    def save(self, credential_record: PasswordCredentialRecord) -> None:
        self._credential_records.append(credential_record)

    def update_password_hash(self, email: str, new_password_hash: bytes) -> None:
        for credential_record in self._credential_records:
            if credential_record.email == email:
                credential_record.password_hash = new_password_hash

    def list_by_principal_id(self, principal_id: UUID) -> list[PasswordCredentialRecord]:
        return [c for c in self._credential_records if c.principal_id == principal_id]

    def get_by_email(self, email: str) -> PasswordCredentialRecord | None:
        return next((c for c in self._credential_records if c.email == email), None)

    def delete_by_principal_id(self, principal_id: UUID) -> None:
        self._credential_records = [c for c in self._credential_records if c.principal_id != principal_id]

from datetime import datetime
from uuid import UUID

from identity_access_management_context.domain.entities import SSOCredentialRecord
from identity_access_management_context.domain.exceptions import (
    SSOCredentialAlreadyExistsException,
)


class FakeSSOCredentialRecordRepository:
    def __init__(self):
        self._credential_records: dict[tuple[str, str], SSOCredentialRecord] = {}

    def create(self, credential_record: SSOCredentialRecord) -> None:
        key = (credential_record.provider, credential_record.subject)
        if key in self._credential_records:
            raise SSOCredentialAlreadyExistsException(
                f"SSO subject {credential_record.subject} with provider {credential_record.provider} already exists"
            )
        self._credential_records[key] = credential_record

    def update_last_login(self, provider: str, subject: str, last_login: datetime) -> None:
        if (provider, subject) in self._credential_records:
            self._credential_records[(provider, subject)].last_login = last_login

    def get_by_subject(self, provider: str, subject: str) -> SSOCredentialRecord | None:
        return self._credential_records.get((provider, subject))

    def get_by_principal_id(self, principal_id: UUID) -> SSOCredentialRecord | None:
        return next((c for c in self._credential_records.values() if c.principal_id == principal_id), None)

from collections.abc import Iterable
from uuid import UUID

from identity_access_management_context.application.gateways import ServiceAccountTokenCredentialRecordRepository
from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord


class FakeServiceAccountTokenCredentialRecordRepository(ServiceAccountTokenCredentialRecordRepository):
    def __init__(self):
        self.credential_records: dict[UUID, ServiceAccountTokenCredentialRecord] = {}

    def create(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        for credential_record in credential_records:
            self.credential_records[credential_record.principal_id] = credential_record

    def replace(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        for credential_record in credential_records:
            self.credential_records[credential_record.principal_id] = credential_record

    def get_by_token_hash(self, token_hash: str) -> ServiceAccountTokenCredentialRecord | None:
        return next((c for c in self.credential_records.values() if c.token_hash == token_hash), None)

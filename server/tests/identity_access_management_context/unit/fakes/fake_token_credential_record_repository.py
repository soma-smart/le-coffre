from collections.abc import Iterable
from uuid import UUID

from identity_access_management_context.application.gateways import TokenCredentialRecordRepository
from identity_access_management_context.domain.entities import TokenCredentialRecord


class FakeTokenCredentialRecordRepository(TokenCredentialRecordRepository):
    def __init__(self):
        self.credential_records: list[TokenCredentialRecord] = []

    def list_by_principal_id(self, principal_id: UUID) -> list[TokenCredentialRecord]:
        """Test helper: the records an account holds."""
        return [c for c in self.credential_records if c.principal_id == principal_id]

    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        self.credential_records.extend(credential_records)

    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> None:
        deleted = set(principal_ids)
        self.credential_records = [c for c in self.credential_records if c.principal_id not in deleted]

    def replace(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        credential_records = list(credential_records)
        self.delete_by_principal_ids(c.principal_id for c in credential_records)
        self.create(credential_records)

    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        return next((c for c in self.credential_records if c.token_hash == token_hash), None)

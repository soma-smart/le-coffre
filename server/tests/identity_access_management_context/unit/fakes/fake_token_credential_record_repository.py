from collections.abc import Iterable
from uuid import UUID

from identity_access_management_context.application.gateways import (
    CannotRotateTokenCredentialError,
    TokenCredentialRecordRepository,
)
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

    def list_by_principal_ids(self, principal_ids: Iterable[UUID]) -> list[TokenCredentialRecord]:
        wanted = set(principal_ids)
        return [c for c in self.credential_records if c.principal_id in wanted]

    def _replace(self, token_hashes: Iterable[str], new_token_hashes: Iterable[str]) -> None:
        new_token_hash_by_old = dict(zip(token_hashes, new_token_hashes, strict=True))
        stored = {c.token_hash for c in self.credential_records}
        # Refused whole, as the SQL adapter does.
        if not stored.issuperset(new_token_hash_by_old):
            raise CannotRotateTokenCredentialError()
        for credential_record in self.credential_records:
            credential_record.token_hash = new_token_hash_by_old.get(
                credential_record.token_hash, credential_record.token_hash
            )

    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        return next((c for c in self.credential_records if c.token_hash == token_hash), None)

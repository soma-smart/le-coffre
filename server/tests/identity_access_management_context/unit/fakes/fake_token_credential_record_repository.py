from collections.abc import Iterable
from datetime import datetime, timedelta
from uuid import UUID

from identity_access_management_context.application.gateways import (
    CannotRotateTokenCredentialError,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.domain.entities import TokenCredentialRecord
from identity_access_management_context.domain.value_objects import TokenCredential


class FakeTokenCredentialRecordRepository(TokenCredentialRecordRepository):
    def __init__(self):
        self.credential_records: list[TokenCredentialRecord] = []

    def issue(self, principal_id: UUID, now: datetime, **lifecycle) -> TokenCredential:
        """Test helper: store a token for this principal, shaped like an extension's unless told otherwise."""
        token = TokenCredential.generate()
        fields = {
            "read_only": True,
            "label": "Browser extension",
            "expires_at": now + timedelta(days=30),
            "last_used_at": now,
            "max_idle": timedelta(days=14),
        } | lifecycle
        self.credential_records.append(
            TokenCredentialRecord(principal_id=principal_id, token_hash=token.hash, **fields)
        )
        return token

    def list_by_principal_id(self, principal_id: UUID) -> list[TokenCredentialRecord]:
        """Test helper: the records an account holds."""
        return [c for c in self.credential_records if c.principal_id == principal_id]

    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        self.credential_records.extend(credential_records)

    def create_within_limit(self, credential_record: TokenCredentialRecord, limit: int, now: datetime) -> bool:
        held = self.list_by_principal_id(credential_record.principal_id)
        if sum(c.is_usable(now) for c in held) >= limit:
            return False
        self.credential_records.append(credential_record)
        return True

    def get_by_id(self, credential_id: UUID) -> TokenCredentialRecord | None:
        return next((c for c in self.credential_records if c.id == credential_id), None)

    def delete(self, credential_ids: Iterable[UUID]) -> int:
        deleted = set(credential_ids)
        kept = [c for c in self.credential_records if c.id not in deleted]
        count = len(self.credential_records) - len(kept)
        self.credential_records = kept
        return count

    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> int:
        deleted = set(principal_ids)
        kept = [c for c in self.credential_records if c.principal_id not in deleted]
        count = len(self.credential_records) - len(kept)
        self.credential_records = kept
        return count

    def touch_last_used(self, credential_id: UUID, now: datetime, coarsening: timedelta) -> None:
        record = self.get_by_id(credential_id)
        if record is not None and (record.last_used_at is None or now - record.last_used_at >= coarsening):
            record.last_used_at = now

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

from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import TokenCredentialRecord


class TokenCredentialRecordRepositoryException(Exception): ...


class CannotRotateTokenCredentialError(TokenCredentialRecordRepositoryException):
    def __init__(self) -> None:
        super().__init__("Some of the token credentials to rotate no longer exist. None were rotated.")


class TokenCredentialRecordRepository(Protocol):
    """Storage for the token hashes that prove principals."""

    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        """Store token credential records, alongside any the principals already hold."""

    def replace_token_hashes(self, token_hashes: Iterable[str], new_token_hashes: Iterable[str]) -> None:
        """Replace token hashes with new token hashes.

        Raises:
            CannotRotateTokenCredentialError: if any of the token hashes is no longer stored. Nothing is replaced then.
        """

    def list_by_principal_ids(self, principal_ids: Iterable[UUID]) -> Sequence[TokenCredentialRecord]:
        """Return every token credential record of these principals."""

    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        """Return the credential record holding this token hash."""

    def create_within_limit(self, credential_record: TokenCredentialRecord, limit: int, now: datetime) -> bool:
        """Store a token credential record unless its principal already holds `limit` usable ones.

        Returns whether it was stored. Counting and storing are one serialised
        step per principal: checked beforehand, two simultaneous issuances could
        both see room for one more.
        """

    def get_by_id(self, credential_id: UUID) -> TokenCredentialRecord | None:
        """Return the token credential record with this id."""

    def delete(self, credential_ids: Iterable[UUID]) -> int:
        """Delete these token credential records. Returns how many existed."""

    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> int:
        """Delete every token credential record of these principals. Returns how many existed."""

    def touch_last_used(self, credential_id: UUID, now: datetime, coarsening: timedelta) -> None:
        """Record that the token was presented, unless it already was less than `coarsening` ago.

        Coarsened so that a busy client does not write on every request.
        """

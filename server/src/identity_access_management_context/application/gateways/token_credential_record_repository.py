from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from identity_access_management_context.domain.entities import TokenCredentialRecord


class TokenCredentialRecordRepository(ABC):
    """Storage for the token hashes that prove principals."""

    @abstractmethod
    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        """Store token credential records, alongside any the principals already hold."""

    @abstractmethod
    def replace(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        """Make each credential record the only one of its principal, deleting the others."""

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        """Return the credential record holding this token hash."""

    @abstractmethod
    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> None:
        """Delete every token credential record of these principals."""

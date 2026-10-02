from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord


class ServiceAccountTokenCredentialRecordRepository(ABC):
    """Storage for the token hashes that prove service accounts."""

    @abstractmethod
    def create(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        """Store token credential records, alongside any the accounts already hold."""

    @abstractmethod
    def replace(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        """Make each credential record the only one of its service account, deleting the others."""

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> ServiceAccountTokenCredentialRecord | None:
        """Return the credential record holding this token hash."""

    @abstractmethod
    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> None:
        """Delete every token credential record of these service accounts."""

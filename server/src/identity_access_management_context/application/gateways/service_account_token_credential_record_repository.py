from abc import ABC, abstractmethod
from collections.abc import Iterable

from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord


class ServiceAccountTokenCredentialRecordRepository(ABC):
    """Storage for the token hashes that prove service accounts."""

    @abstractmethod
    def create(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        """Store the first token credential record of new service accounts."""

    @abstractmethod
    def replace(self, credential_records: Iterable[ServiceAccountTokenCredentialRecord]) -> None:
        """Make each credential record the only one of its service account."""

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> ServiceAccountTokenCredentialRecord | None:
        """Return the credential record holding this token hash."""

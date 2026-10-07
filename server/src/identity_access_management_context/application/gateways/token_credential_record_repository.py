from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from uuid import UUID

from identity_access_management_context.domain.entities import TokenCredentialRecord
from identity_access_management_context.domain.value_objects.token_credential import TokenCredential


class TokenCredentialRecordRepositoryException(Exception): ...


class CannotRotateTokenCredentialError(TokenCredentialRecordRepositoryException):
    def __init__(self) -> None:
        super().__init__("Some of the token credentials to rotate no longer exist. None were rotated.")


class TokenCredentialRecordRepository(ABC):
    """Storage for the token hashes that prove principals."""

    @abstractmethod
    def create(self, credential_records: Iterable[TokenCredentialRecord]) -> None:
        """Store token credential records, alongside any the principals already hold."""

    @abstractmethod
    def _replace(self, token_hashes: Iterable[str], new_token_hashes: Iterable[str]) -> None:
        """Replace token hashes with new token hashes.

        Raises:
            CannotRotateTokenCredentialError: if any of the token hashes is no longer stored. Nothing is replaced then.
        """

    @abstractmethod
    def list_by_principal_ids(self, principal_ids: Iterable[UUID]) -> Sequence[TokenCredentialRecord]:
        """Return every token credential record of these principals."""

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> TokenCredentialRecord | None:
        """Return the credential record holding this token hash."""

    @abstractmethod
    def delete_by_principal_ids(self, principal_ids: Iterable[UUID]) -> None:
        """Delete every token credential record of these principals."""

    def rotate(self, token_hashes: Iterable[str]) -> Sequence[str]:
        """Rotate token hashes.

        Raises:
            CannotRotateTokenCredentialError: If something happened while rotating. Nothing is rotated then.
        """
        if not (_token_hashes := tuple(token_hashes)):
            return ()

        # Generate new tokens
        new_credentials = (TokenCredential.generate() for _ in _token_hashes)
        new_token_hashes, new_tokens = zip(
            *((credential.hash, credential.value) for credential in new_credentials),
            strict=True,
        )

        # Replace them
        self._replace(_token_hashes, new_token_hashes)

        return new_tokens

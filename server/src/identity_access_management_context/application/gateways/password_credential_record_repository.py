from abc import ABC, abstractmethod
from uuid import UUID

from identity_access_management_context.domain.entities import PasswordCredentialRecord


class PasswordCredentialRecordRepository(ABC):
    @abstractmethod
    def save(self, credential_record: PasswordCredentialRecord) -> None:
        """Save a password credential record"""

    @abstractmethod
    def update_password_hash(self, email: str, new_password_hash: bytes) -> None:
        """Replace the password hash of the credential record holding this email"""

    @abstractmethod
    def list_by_principal_id(self, principal_id: UUID) -> list[PasswordCredentialRecord]:
        """List every password credential record of a principal"""

    @abstractmethod
    def get_by_email(self, email: str) -> PasswordCredentialRecord | None:
        """Get the password credential record holding this email"""

    @abstractmethod
    def delete_by_principal_id(self, principal_id: UUID) -> None:
        """Delete every password credential record of a principal.

        Must run whenever the user itself is deleted. A credential row that
        outlives its user shadows any account later created with the same
        email, and is an authentication secret nobody can see or revoke.
        """

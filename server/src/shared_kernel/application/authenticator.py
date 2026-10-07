from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared_kernel.application.gateways import PrincipalRepository
from shared_kernel.domain.entities import CredentialRecord, Principal
from shared_kernel.domain.exceptions import OrphanedCredentialError, RejectedCredentialError
from shared_kernel.domain.value_objects import Credential


@dataclass(frozen=True)
class Authenticator[C: Credential, R: CredentialRecord](ABC):
    """Turns one kind of `Credential` into the `Principal` it proves.

    Every kind proves the same way: find the record holding the credential,
    check the credential against it, then load whichever principal the record
    points to. The kind of credential says nothing about the kind of principal.
    """

    principal_repository: PrincipalRepository

    @abstractmethod
    def _retrieve(self, credential: C) -> R:
        """Return the record holding this credential.

        Raises:
            UnknownCredentialError: if no record holds it.
        """

    @abstractmethod
    def _check(self, credential: C, credential_record: R) -> bool:
        """Tell whether the credential matches the record holding it."""

    def authenticate(self, credential: C) -> Principal:
        """Return the principal behind this proof.

        Raises:
            UnknownCredentialError: if no record holds the credential.
            RejectedCredentialError: if the credential does not match its record.
            OrphanedCredentialError: if the record's principal no longer exists.
        """
        credential_record = self._retrieve(credential)
        if not self._check(credential, credential_record):
            raise RejectedCredentialError()
        principal = self.principal_repository.get_by_id(credential_record.principal_id)
        if principal is None:
            raise OrphanedCredentialError()
        return principal

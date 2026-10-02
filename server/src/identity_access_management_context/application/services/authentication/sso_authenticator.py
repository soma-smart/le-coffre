from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import SSOCredentialRecordRepository, UserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    OrphanedSSOCredentialError,
    UnknownSSOSubjectError,
)
from identity_access_management_context.domain.value_objects import SSOCredential
from shared_kernel.application.authenticator import Authenticator


@dataclass(frozen=True)
class SSOAuthenticator(Authenticator[SSOCredential]):
    """Resolves a subject the SSO provider vouched for to the user it is linked to.

    The provider already proved the subject during the code exchange; what is
    left is finding whose it is.
    """

    sso_credential_record_repository: SSOCredentialRecordRepository
    user_repository: UserRepository

    @override
    def authenticate(self, credential: SSOCredential) -> User:
        """Return the user linked to this subject.

        Raises:
            UnknownSSOSubjectError: if no user is linked to the subject yet.
            OrphanedSSOCredentialError: if the linked user no longer exists.
        """
        credential_record = self.sso_credential_record_repository.get_by_subject(
            credential.provider, credential.subject
        )
        if credential_record is None:
            raise UnknownSSOSubjectError()

        user = self.user_repository.get_by_id(credential_record.principal_id)
        if user is None:
            raise OrphanedSSOCredentialError()
        return user

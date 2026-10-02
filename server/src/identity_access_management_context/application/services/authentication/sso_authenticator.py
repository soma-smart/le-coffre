from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import SSOCredentialRecordRepository
from identity_access_management_context.domain.entities import SSOCredentialRecord
from identity_access_management_context.domain.value_objects import SSOCredential
from shared_kernel.application.authenticator import Authenticator
from shared_kernel.domain.exceptions import UnknownCredentialError


@dataclass(frozen=True)
class SSOAuthenticator(Authenticator[SSOCredential, SSOCredentialRecord]):
    """Resolves a subject the SSO provider vouched for to the principal it is linked to."""

    sso_credential_record_repository: SSOCredentialRecordRepository

    @override
    def _retrieve(self, credential: SSOCredential) -> SSOCredentialRecord:
        credential_record = self.sso_credential_record_repository.get_by_subject(
            credential.provider, credential.subject
        )
        if credential_record is None:
            raise UnknownCredentialError()
        return credential_record

    @override
    def _check(self, credential: SSOCredential, credential_record: SSOCredentialRecord) -> bool:
        # The SSO provider is the one responsible for checking
        return True

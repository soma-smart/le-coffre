from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import ServiceAccountTokenCredentialRecordRepository
from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.application.authenticator import Authenticator
from shared_kernel.domain.exceptions import UnknownCredentialError


@dataclass(frozen=True)
class ServiceAccountTokenAuthenticator(Authenticator[ServiceAccountToken, ServiceAccountTokenCredentialRecord]):
    """Resolves a service-account token to the principal holding it.

    A value that does not parse never gets here: building the ServiceAccountToken
    is what rejects it, before any lookup. A revoked account holds no token
    any more, so it is never found.
    """

    service_account_token_credential_record_repository: ServiceAccountTokenCredentialRecordRepository

    @override
    def _retrieve(self, credential: ServiceAccountToken) -> ServiceAccountTokenCredentialRecord:
        credential_record = self.service_account_token_credential_record_repository.get_by_token_hash(credential.hash)
        if credential_record is None:
            raise UnknownCredentialError()
        return credential_record

    @override
    def _check(self, credential: ServiceAccountToken, credential_record: ServiceAccountTokenCredentialRecord) -> bool:
        # The token is 256 bits of randomness, finding a record by its hash is the proof.
        return True

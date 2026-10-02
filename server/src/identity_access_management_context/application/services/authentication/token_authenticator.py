from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import TokenCredentialRecordRepository
from identity_access_management_context.domain.entities import TokenCredentialRecord
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.application.authenticator import Authenticator
from shared_kernel.domain.exceptions import UnknownCredentialError


@dataclass(frozen=True)
class TokenAuthenticator(Authenticator[TokenCredential, TokenCredentialRecord]):
    """Resolves a token to the principal holding it.

    A value that does not parse never gets here: building the TokenCredential
    is what rejects it, before any lookup. A principal whose token records were
    deleted, like a revoked service account, is never found.
    """

    token_credential_record_repository: TokenCredentialRecordRepository

    @override
    def _retrieve(self, credential: TokenCredential) -> TokenCredentialRecord:
        credential_record = self.token_credential_record_repository.get_by_token_hash(credential.hash)
        if credential_record is None:
            raise UnknownCredentialError()
        return credential_record

    @override
    def _check(self, credential: TokenCredential, credential_record: TokenCredentialRecord) -> bool:
        # The token is 256 bits of randomness, finding a record by its hash is the proof.
        return True

from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import (
    PasswordCredentialRecordRepository,
    PasswordHashingGateway,
)
from identity_access_management_context.domain.entities import PasswordCredentialRecord
from identity_access_management_context.domain.value_objects import PasswordCredential
from shared_kernel.application.authenticator import Authenticator
from shared_kernel.domain.exceptions import UnknownCredentialError

# Pre-computed bcrypt hash used for constant-time password verification when
# user is not found. This prevents timing oracles that could enumerate valid
# emails by measuring response latency differences.
# Generated with: bcrypt.hashpw(hashlib.sha256(b"dummy").digest(), bcrypt.gensalt())
# Note: BcryptHashingGateway pre-hashes all passwords with SHA-256 before bcrypt.
# See: SECURITY.md#timing-attack-mitigations, AUTH-VULN-09
DUMMY_PASSWORD_HASH = b"$2b$12$bTnGLyMH2BYn4GtQhHPnVO33O1fpWb35NL/jHzxbboHURr26xGAu6"


@dataclass(frozen=True)
class PasswordAuthenticator(Authenticator[PasswordCredential, PasswordCredentialRecord]):
    """Resolves an email and password to the principal whose password credential they match."""

    password_credential_record_repository: PasswordCredentialRecordRepository
    password_hashing_gateway: PasswordHashingGateway

    @override
    def _retrieve(self, credential: PasswordCredential) -> PasswordCredentialRecord:
        credential_record = self.password_credential_record_repository.get_by_email(credential.email)
        if credential_record is None:
            # Always call verify the password with a dummy hash to prevent timing oracles
            self.password_hashing_gateway.verify(credential.password, DUMMY_PASSWORD_HASH)
            raise UnknownCredentialError()
        return credential_record

    @override
    def _check(self, credential: PasswordCredential, credential_record: PasswordCredentialRecord) -> bool:
        return self.password_hashing_gateway.verify(credential.password, credential_record.password_hash)

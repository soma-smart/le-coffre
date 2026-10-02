from dataclasses import dataclass
from typing import override

from identity_access_management_context.application.gateways import (
    PasswordCredentialRecordRepository,
    PasswordHashingGateway,
    UserRepository,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import (
    OrphanedPasswordCredentialError,
    UnknownPasswordEmailError,
    WrongPasswordError,
)
from identity_access_management_context.domain.value_objects import PasswordCredential
from shared_kernel.application.authenticator import Authenticator

# Pre-computed bcrypt hash used for constant-time password verification when
# user is not found. This prevents timing oracles that could enumerate valid
# emails by measuring response latency differences.
# Generated with: bcrypt.hashpw(hashlib.sha256(b"dummy").digest(), bcrypt.gensalt())
# Note: BcryptHashingGateway pre-hashes all passwords with SHA-256 before bcrypt.
# See: SECURITY.md#timing-attack-mitigations, AUTH-VULN-09
DUMMY_PASSWORD_HASH = b"$2b$12$bTnGLyMH2BYn4GtQhHPnVO33O1fpWb35NL/jHzxbboHURr26xGAu6"


@dataclass(frozen=True)
class PasswordAuthenticator(Authenticator[PasswordCredential]):
    """Resolves an email and password to the user whose password credential they match."""

    password_credential_record_repository: PasswordCredentialRecordRepository
    user_repository: UserRepository
    password_hashing_gateway: PasswordHashingGateway

    @override
    def authenticate(self, credential: PasswordCredential) -> User:
        """Return the user these credentials belong to.

        Raises:
            PasswordAuthenticationError: one subclass per reason the proof fails.
        """
        credential_record = self.password_credential_record_repository.get_by_email(credential.email)
        if credential_record is None:
            # Always call bcrypt.verify() with a dummy hash to prevent timing oracles
            self.password_hashing_gateway.verify(credential.password, DUMMY_PASSWORD_HASH)
            raise UnknownPasswordEmailError()

        if not self.password_hashing_gateway.verify(credential.password, credential_record.password_hash):
            raise WrongPasswordError()

        user = self.user_repository.get_by_id(credential_record.principal_id)
        if user is None:
            # Credentials with no user behind them are an inconsistency
            raise OrphanedPasswordCredentialError()
        return user

from dataclasses import dataclass, field

from shared_kernel.domain.entities.credential_record import CredentialRecord


@dataclass(kw_only=True)
class PasswordCredentialRecord(CredentialRecord):
    """A password hash, found by the email a user logs in with."""

    email: str
    password_hash: bytes = field(repr=False)

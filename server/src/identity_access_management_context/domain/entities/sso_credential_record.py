from dataclasses import dataclass
from datetime import datetime

from shared_kernel.domain.entities.credential_record import CredentialRecord


@dataclass(kw_only=True)
class SSOCredentialRecord(CredentialRecord):
    """The subject an SSO provider vouches for, linked to the user it signs in."""

    provider: str
    subject: str
    created_at: datetime | None = None
    last_login: datetime | None = None

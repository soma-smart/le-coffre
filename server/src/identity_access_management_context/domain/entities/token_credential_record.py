from dataclasses import dataclass

from shared_kernel.domain.entities.credential_record import CredentialRecord


@dataclass(kw_only=True)
class TokenCredentialRecord(CredentialRecord):
    """The hash of the token a principal presents.

    Only the hash is kept: the token itself is shown once, when issued.
    """

    token_hash: str

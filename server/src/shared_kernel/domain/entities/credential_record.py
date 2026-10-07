from dataclasses import dataclass
from uuid import UUID


@dataclass(kw_only=True)
class CredentialRecord:
    """What is kept to check a presented `Credential` against.

    It points to the one principal it proves, and holds nothing else here: the
    stored verifier itself depends on the kind of credential.
    """

    principal_id: UUID

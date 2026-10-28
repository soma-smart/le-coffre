from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class CredentialRecord:
    """What is kept to check a presented `Credential` against.

    It points to the one principal it proves, and holds nothing else here: the
    stored verifier itself depends on the kind of credential.
    """

    id: UUID = field(default_factory=uuid4)
    principal_id: UUID

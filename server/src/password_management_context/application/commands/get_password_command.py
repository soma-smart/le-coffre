from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetPasswordCommand:
    requester_id: UUID
    password_id: UUID
    # Recorded with the access, not used to decide it: after a stolen token,
    # the audit trail has to say which reads were that token's. None when the
    # caller authenticated with its session.
    credential_id: UUID | None = None

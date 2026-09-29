from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.value_objects import CredentialKind


@dataclass
class GetPasswordCommand:
    requester_id: UUID
    password_id: UUID
    # Recorded with the access, not used to decide it: after a stolen
    # extension token, the audit trail has to say which reads were the
    # extension's and which were the user's own browser.
    credential_kind: CredentialKind = CredentialKind.SESSION

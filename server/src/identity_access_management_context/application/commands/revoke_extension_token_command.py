from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.entities import ValidatedUser


@dataclass
class RevokeExtensionTokenCommand:
    token_id: UUID
    requesting_user: ValidatedUser

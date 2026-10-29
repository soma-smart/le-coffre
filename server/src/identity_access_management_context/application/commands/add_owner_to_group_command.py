from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class AddOwnerToGroupCommand:
    requesting_user: AuthenticatedUser
    group_id: UUID
    user_id: UUID

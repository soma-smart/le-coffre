from dataclasses import dataclass
from uuid import UUID

from shared_kernel.authentication import AuthenticatedUser


@dataclass
class DeleteGroupCommand:
    requesting_user: AuthenticatedUser
    group_id: UUID

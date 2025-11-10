from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain import AuthenticatedUser


@dataclass
class DeleteUserCommand:
    requesting_user: AuthenticatedUser
    user_id: UUID

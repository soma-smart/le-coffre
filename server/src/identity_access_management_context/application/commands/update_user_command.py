from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class UpdateUserCommand:
    requesting_user: AuthenticatedUser
    id: UUID
    username: str
    email: str
    name: str

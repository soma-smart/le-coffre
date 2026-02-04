from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class PromoteAdminCommand:
    requesting_user: AuthenticatedUser
    user_id: UUID

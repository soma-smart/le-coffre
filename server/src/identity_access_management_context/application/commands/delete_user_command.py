from dataclasses import dataclass
from uuid import UUID

from identity_access_management_context.adapters.primary.dependencies import (
    AuthenticatedUser,
)


@dataclass
class DeleteUserCommand:
    requesting_user: AuthenticatedUser
    user_id: UUID

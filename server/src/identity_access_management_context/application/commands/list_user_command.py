from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ListUserCommand:
    requesting_user: AuthenticatedUser

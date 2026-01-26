from dataclasses import dataclass
from shared_kernel.authentication import AuthenticatedUser


@dataclass
class ListUserCommand:
    requesting_user: AuthenticatedUser

from dataclasses import dataclass
from shared_kernel.authentication import AuthenticatedUser


@dataclass(frozen=True)
class IsSsoConfigSetCommand:
    requesting_user: AuthenticatedUser

from dataclasses import dataclass
from shared_kernel.authentication import AuthenticatedUser


@dataclass
class LockVaultCommand:
    requesting_user: AuthenticatedUser

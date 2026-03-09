from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class LockVaultCommand:
    requesting_user: AuthenticatedUser

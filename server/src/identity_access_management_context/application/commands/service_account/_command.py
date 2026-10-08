from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ServiceAccountCommand:
    requesting_user: AuthenticatedUser
    """User requesting the command."""

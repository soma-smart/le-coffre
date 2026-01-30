from dataclasses import dataclass
from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ListEventCommand:
    requesting_user: AuthenticatedUser

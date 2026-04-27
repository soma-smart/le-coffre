from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class GetStatisticForAdminCommand:
    requesting_user: AuthenticatedUser

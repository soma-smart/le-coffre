from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class GetPasswordStatisticForAdminCommand:
    requesting_user: AuthenticatedUser

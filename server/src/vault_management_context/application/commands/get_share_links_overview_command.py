from dataclasses import dataclass

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class GetShareLinksOverviewCommand:
    requesting_user: AuthenticatedUser

from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ListOneTimeLinksForAdminCommand:
    requesting_user: AuthenticatedUser
    include_inactive: bool = False


@dataclass
class RevokeOneTimeLinkForAdminCommand:
    link_id: UUID
    requesting_user: AuthenticatedUser


@dataclass
class RevokeAllOneTimeLinksForUserCommand:
    target_user_id: UUID
    requesting_user: AuthenticatedUser


@dataclass
class ListMyOneTimeLinksCommand:
    requesting_user_id: UUID
    include_inactive: bool = False

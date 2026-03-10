from dataclasses import dataclass, field
from uuid import UUID

from identity_access_management_context.domain.constants import ADMIN_ROLE
from identity_access_management_context.domain.exceptions import (
    UserAlreadyAdminException,
)


@dataclass
class User:
    id: UUID
    username: str
    email: str
    name: str
    roles: list[str] = field(default_factory=list)

    def promote_to_admin(self) -> None:
        if ADMIN_ROLE in self.roles:
            raise UserAlreadyAdminException(self.id)
        self.roles.append(ADMIN_ROLE)

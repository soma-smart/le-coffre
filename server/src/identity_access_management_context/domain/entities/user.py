from dataclasses import dataclass, field
from datetime import datetime
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
    current_refresh_token_jti: str | None = None
    session_invalid_before: datetime | None = None

    def promote_to_admin(self) -> None:
        if ADMIN_ROLE in self.roles:
            raise UserAlreadyAdminException(self.id)
        self.roles.append(ADMIN_ROLE)

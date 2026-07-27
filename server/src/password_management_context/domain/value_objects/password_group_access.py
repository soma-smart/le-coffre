from dataclasses import dataclass, field
from datetime import datetime

from password_management_context.domain.value_objects.password_permission import (
    PasswordPermission,
)


@dataclass(frozen=True)
class PasswordGroupAccess:
    """What one group may do with one password, and until when.

    This is the single answer the permission repository gives about a group, and
    therefore the single place access decisions are made. Expiry is carried here
    rather than checked by each caller so that no decider can read the permission
    set while forgetting the deadline attached to it.

    Ownership is stored in its own table and carries no deadline: an owner can
    never be timed out of their own password.
    """

    is_owner: bool
    permissions: set[PasswordPermission] = field(default_factory=set)
    expires_at: datetime | None = None

    def is_expired(self, now: datetime) -> bool:
        if self.is_owner or self.expires_at is None:
            return False
        return now >= self.expires_at

    def is_active(self, now: datetime) -> bool:
        return not self.is_expired(now)

    def grants_read(self, now: datetime) -> bool:
        has_read = self.is_owner or PasswordPermission.READ in self.permissions
        return has_read and self.is_active(now)

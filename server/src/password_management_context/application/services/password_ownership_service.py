"""Service resolving who owns a password"""

from uuid import UUID

from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.domain.exceptions import NotPasswordOwnerError


class PasswordOwnershipService:
    """Answers "does this user own this password".

    Ownership is held by a group, not a user: a password has one owning group
    (the Ownership table), and a user owns the password when they own that
    group. The same walk is currently inlined in several use cases; new code
    goes through here instead.
    """

    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway

    def ensure_user_owns_password(self, user_id: UUID, password_id: UUID) -> UUID:
        """Return the owning group id, or raise if the user is not an owner."""
        # Raises PasswordNotFoundError itself when the password is gone; called
        # for that check alone, so a missing password never reads as "not owner".
        self.password_repository.get_by_id(password_id)

        owner_group_id = self._find_owner_group_id(password_id)
        if owner_group_id is None:
            raise NotPasswordOwnerError(user_id, password_id)

        if not self.group_access_gateway.is_user_owner_of_group(user_id, owner_group_id):
            raise NotPasswordOwnerError(user_id, password_id)

        return owner_group_id

    def _find_owner_group_id(self, password_id: UUID) -> UUID | None:
        all_permissions = self.password_permissions_repository.list_all_permissions_for(password_id)
        for group_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                return group_id
        return None

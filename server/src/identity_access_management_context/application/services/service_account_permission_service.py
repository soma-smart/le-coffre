from dataclasses import dataclass
from uuid import UUID

from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
)
from identity_access_management_context.domain.entities import Group
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ServiceAccountPermissionService:
    """Answers "may this user manage this group's service accounts".

    Unlike deleting or updating a group, admins do not pass here: a service
    account is a working credential, and admins are deliberately unable to read
    the passwords of groups they don't belong to (members may use a group to
    store private passwords). Letting an admin mint or rotate a service account
    on any group would hand them a way around that boundary. Only an owner of
    the group may manage its service accounts.

    Deliberately says nothing about personal groups. They are undeletable and
    unmodifiable elsewhere, but a personal group is exactly where a solo user
    needs a service account, so the personal-group guard that surrounds the
    other group operations must not be copied here.
    """

    group_repository: GroupRepository
    """Group repository."""

    group_member_repository: GroupMemberRepository
    """Group member repository."""

    def ensure_user_can_manage_group(self, requesting_user: AuthenticatedUser, group_id: UUID) -> Group:
        """Return the group, or raise if the user may not manage its service accounts.

        Returns the group so a caller needing it does not read it twice.
        """
        group = self.group_repository.get_by_id(group_id)
        if group is None:
            raise GroupNotFoundException(group_id)

        if not self.group_member_repository.is_owner(group_id, requesting_user.user_id):
            raise UserNotOwnerOfGroupException(requesting_user.user_id, group_id)

        return group

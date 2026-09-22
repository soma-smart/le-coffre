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
from shared_kernel.domain.services import AdminPermissionChecker


@dataclass
class GroupManagementPermissionService:
    """Answers "may this user manage this group's credentials".

    Admins pass, as they do for deleting and updating a group. Otherwise the
    user has to be an owner: being a plain member is not enough, because minting
    a credential on a group grants whatever that group can reach.

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
        """Return the group, or raise if the user may not manage it.

        Returns the group so a caller needing it does not read it twice.
        """
        group = self.group_repository.get_by_id(group_id)
        if group is None:
            raise GroupNotFoundException(group_id)

        if AdminPermissionChecker.is_admin(requesting_user):
            return group

        if not self.group_member_repository.is_owner(group_id, requesting_user.user_id):
            raise UserNotOwnerOfGroupException(requesting_user.user_id, group_id)

        return group

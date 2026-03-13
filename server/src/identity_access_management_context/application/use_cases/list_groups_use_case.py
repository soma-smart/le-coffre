from identity_access_management_context.application.commands import ListGroupsCommand
from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
)
from identity_access_management_context.application.responses import (
    GroupResponse,
    ListGroupResponse,
)
from shared_kernel.application.tracing import TracedUseCase


class ListGroupsUseCase(TracedUseCase):
    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository

    def execute(self, command: ListGroupsCommand) -> ListGroupResponse:
        """List all groups with their owners, optionally filtering out personal groups.

        Args:
            command: Contains requesting_user and include_personal flag

        Returns:
            List of groups with owners based on filter criteria.
        """
        all_groups = self.group_repository.get_all()

        if not command.include_personal:
            all_groups = [group for group in all_groups if not group.is_personal]

        result = ListGroupResponse([])
        for group in all_groups:
            members = self.group_member_repository.get_members(group.id)
            owner_ids = [m.user_id for m in members if m.is_owner]
            members_ids = [m.user_id for m in members if not m.is_owner]

            # For personal groups, the user_id is the owner if no members in table
            if group.is_personal and group.user_id and not owner_ids:
                owner_ids = [group.user_id]

            result.groups.append(
                GroupResponse(
                    id=group.id,
                    name=group.name,
                    is_personal=group.is_personal,
                    user_id=group.user_id,
                    owners=owner_ids,
                    members=members_ids,
                )
            )

        return result

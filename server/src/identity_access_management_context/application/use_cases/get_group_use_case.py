from identity_access_management_context.application.commands import GetGroupCommand
from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
)
from identity_access_management_context.application.responses import GetGroupResponse
from identity_access_management_context.domain.exceptions import GroupNotFoundException
from shared_kernel.application.tracing import TracedUseCase


class GetGroupUseCase(TracedUseCase):
    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository

    def execute(self, command: GetGroupCommand) -> GetGroupResponse:
        group = self.group_repository.get_by_id(command.group_id)
        if not group:
            raise GroupNotFoundException(command.group_id)

        members = self.group_member_repository.get_members(command.group_id)

        return GetGroupResponse(group=group, members=members)

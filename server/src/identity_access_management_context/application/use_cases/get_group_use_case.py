from uuid import UUID
from dataclasses import dataclass

from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.entities import Group, GroupMember
from identity_access_management_context.domain.exceptions import GroupNotFoundException


@dataclass
class GetGroupResponse:
    group: Group
    members: list[GroupMember]


class GetGroupUseCase:
    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository

    def execute(self, group_id: UUID) -> GetGroupResponse:
        group = self.group_repository.get_by_id(group_id)
        if not group:
            raise GroupNotFoundException(group_id)

        members = self.group_member_repository.get_members(group_id)

        return GetGroupResponse(group=group, members=members)

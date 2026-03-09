from dataclasses import dataclass

from identity_access_management_context.domain.entities import Group, GroupMember


@dataclass
class GetGroupResponse:
    group: Group
    members: list[GroupMember]

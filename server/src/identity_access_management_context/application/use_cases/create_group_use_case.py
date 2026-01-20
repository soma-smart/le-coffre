from uuid import UUID

from identity_access_management_context.application.commands import CreateGroupCommand
from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.entities import Group
from identity_access_management_context.domain.exceptions import UserNotFoundException


class CreateGroupUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository

    def execute(self, command: CreateGroupCommand) -> UUID:
        user = self.user_repository.get_by_id(command.creator_id)
        if user is None:
            raise UserNotFoundException(command.creator_id)

        group = Group(
            id=command.id,
            name=command.name,
            is_personal=False,
        )

        self.group_repository.save_group(group)
        self.group_member_repository.add_member(
            command.id, command.creator_id, is_owner=True
        )

        return group.id

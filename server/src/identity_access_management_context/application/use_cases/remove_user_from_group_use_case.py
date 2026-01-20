from identity_access_management_context.application.commands import (
    RemoveUserFromGroupCommand,
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
    UserNotMemberOfGroupException,
    CannotRemoveOwnerException,
)


class RemoveUserFromGroupUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository

    def execute(self, command: RemoveUserFromGroupCommand) -> None:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if group.is_personal:
            raise CannotModifyPersonalGroupException(command.group_id)

        if not self.group_member_repository.is_owner(
            command.group_id, command.requester_id
        ):
            raise UserNotOwnerOfGroupException(command.requester_id, command.group_id)

        if not self.group_member_repository.is_member(
            command.group_id, command.user_id
        ):
            raise UserNotMemberOfGroupException(command.user_id, command.group_id)

        if self.group_member_repository.is_owner(command.group_id, command.user_id):
            raise CannotRemoveOwnerException(command.user_id, command.group_id)

        self.group_member_repository.remove_member(command.group_id, command.user_id)

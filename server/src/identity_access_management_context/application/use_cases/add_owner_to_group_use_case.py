from identity_access_management_context.application.commands import (
    AddOwnerToGroupCommand,
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.exceptions import (
    UserNotOwnerOfGroupException,
    GroupNotFoundException,
    CannotModifyPersonalGroupException,
    UserNotFoundException,
    UserNotMemberOfGroupException,
)


class AddOwnerToGroupUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository

    def execute(self, command: AddOwnerToGroupCommand) -> None:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if group.is_personal:
            raise CannotModifyPersonalGroupException(command.group_id)

        if not self.group_member_repository.is_owner(
            command.group_id, command.requester_id
        ):
            raise UserNotOwnerOfGroupException(command.requester_id, command.group_id)

        user = self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        if not self.group_member_repository.is_member(
            command.group_id, command.user_id
        ):
            raise UserNotMemberOfGroupException(command.user_id, command.group_id)

        self.group_member_repository.add_member(
            command.group_id, command.user_id, is_owner=True
        )

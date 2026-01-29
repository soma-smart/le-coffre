from identity_access_management_context.application.commands import DeleteGroupCommand
from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
    GroupUsageGateway,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotDeletePersonalGroupException,
    CannotDeleteGroupStillUsedException,
)
from shared_kernel.authentication import AdminPermissionChecker


class DeleteGroupUseCase:
    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        group_usage_gateway: GroupUsageGateway,
    ):
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self.group_usage_gateway = group_usage_gateway

    def execute(self, command: DeleteGroupCommand) -> None:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if group.is_personal:
            raise CannotDeletePersonalGroupException(command.group_id)

        # Check if user is admin OR owner of the group
        is_admin = AdminPermissionChecker.is_admin(command.requesting_user)
        is_owner = self.group_member_repository.is_owner(
            command.group_id, command.requesting_user.user_id
        )

        if not (is_admin or is_owner):
            raise UserNotOwnerOfGroupException(
                command.requesting_user.user_id, command.group_id
            )

        if self.group_usage_gateway.is_group_used(command.group_id):
            raise CannotDeleteGroupStillUsedException(command.group_id)

        self.group_member_repository.delete_by_group_id(command.group_id)
        self.group_repository.delete_group(command.group_id)

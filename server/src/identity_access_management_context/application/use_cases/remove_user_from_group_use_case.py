from identity_access_management_context.application.commands import (
    RemoveUserFromGroupCommand,
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.events import UserRemovedFromGroupEvent
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
    UserNotMemberOfGroupException,
    CannotRemoveOwnerException,
)
from shared_kernel.application.gateways import DomainEventPublisher


class RemoveUserFromGroupUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self._event_publisher = event_publisher

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

        self._event_publisher.publish(UserRemovedFromGroupEvent(
            group_id=command.group_id,
            user_id=command.user_id,
            removed_by_user_id=command.requester_id,
        ))

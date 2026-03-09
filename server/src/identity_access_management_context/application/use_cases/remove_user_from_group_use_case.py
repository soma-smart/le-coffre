from identity_access_management_context.application.commands import (
    RemoveUserFromGroupCommand,
)
from identity_access_management_context.application.gateways import (
    GroupEventRepository,
    GroupMemberRepository,
    GroupRepository,
    UserRepository,
)
from identity_access_management_context.domain.events import UserRemovedFromGroupEvent
from identity_access_management_context.domain.exceptions import (
    CannotModifyPersonalGroupException,
    CannotRemoveOwnerException,
    GroupNotFoundException,
    UserNotMemberOfGroupException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase


class RemoveUserFromGroupUseCase(TracedUseCase):
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
        group_event_repository: GroupEventRepository,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self._event_publisher = event_publisher
        self._group_event_repository = group_event_repository

    def execute(self, command: RemoveUserFromGroupCommand) -> None:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if group.is_personal:
            raise CannotModifyPersonalGroupException(command.group_id)

        if not self.group_member_repository.is_owner(command.group_id, command.requester_id):
            raise UserNotOwnerOfGroupException(command.requester_id, command.group_id)

        if not self.group_member_repository.is_member(command.group_id, command.user_id):
            raise UserNotMemberOfGroupException(command.user_id, command.group_id)

        if self.group_member_repository.is_owner(command.group_id, command.user_id):
            raise CannotRemoveOwnerException(command.user_id, command.group_id)

        self.group_member_repository.remove_member(command.group_id, command.user_id)

        event = UserRemovedFromGroupEvent(
            group_id=command.group_id,
            user_id=command.user_id,
            removed_by_user_id=command.requester_id,
        )
        self._event_publisher.publish(event)
        self._group_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requester_id,
            event_data={"group_id": str(command.group_id), "user_id": str(command.user_id)},
        )

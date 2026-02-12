from identity_access_management_context.application.commands import (
    AddUserToGroupCommand,
)
from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
    GroupEventRepository,
)
from identity_access_management_context.domain.events import UserAddedToGroupEvent
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
)
from shared_kernel.application.gateways import DomainEventPublisher


class AddUserToGroupUseCase:
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

    def execute(self, command: AddUserToGroupCommand) -> None:
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
            self.group_member_repository.add_member(
                command.group_id, command.user_id, is_owner=False
            )
            event = UserAddedToGroupEvent(
                group_id=command.group_id,
                user_id=command.user_id,
                added_by_user_id=command.requester_id,
            )
            self._event_publisher.publish(event)
            self._group_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=command.requester_id,
                event_data={"group_id": str(command.group_id), "user_id": str(command.user_id)},
            )

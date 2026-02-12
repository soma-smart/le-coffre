from uuid import UUID

from identity_access_management_context.application.commands import CreateGroupCommand
from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
    GroupEventRepository,
)
from identity_access_management_context.domain.entities import Group
from identity_access_management_context.domain.events import GroupCreatedEvent
from identity_access_management_context.domain.exceptions import UserNotFoundException
from shared_kernel.application.gateways import DomainEventPublisher


class CreateGroupUseCase:
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

        event = GroupCreatedEvent(
            group_id=group.id,
            group_name=group.name,
            created_by_user_id=command.creator_id,
        )
        self._event_publisher.publish(event)
        self._group_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.creator_id,
            event_data={"group_id": str(group.id), "group_name": group.name},
        )

        return group.id

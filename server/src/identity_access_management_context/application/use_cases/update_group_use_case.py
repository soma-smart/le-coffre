from identity_access_management_context.application.commands import (
    UpdateGroupCommand,
)
from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
    IamEventRepository,
)
from identity_access_management_context.domain.events import GroupUpdatedEvent
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.domain.services import AdminPermissionChecker


class UpdateGroupUseCase:
    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
        iam_event_repository: IamEventRepository,
    ):
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self._event_publisher = event_publisher
        self._iam_event_repository = iam_event_repository

    def execute(self, command: UpdateGroupCommand) -> None:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if group.is_personal:
            raise CannotModifyPersonalGroupException(command.group_id)

        if not self.group_member_repository.is_owner(
            command.group_id, command.requesting_user.user_id
        ) and not AdminPermissionChecker().is_admin(command.requesting_user):
            raise UserNotOwnerOfGroupException(
                command.requesting_user.user_id, command.group_id
            )

        group.name = command.name
        self.group_repository.save_group(group)

        event = GroupUpdatedEvent(
            group_id=command.group_id,
            new_name=command.name,
            updated_by_user_id=command.requesting_user.user_id,
        )
        self._event_publisher.publish(event)
        self._iam_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requesting_user.user_id,
            event_data={"group_id": str(command.group_id), "new_name": command.name},
        )

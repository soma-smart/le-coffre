from uuid import UUID

from identity_access_management_context.application.commands import (
    ListGroupEventsCommand,
)
from identity_access_management_context.application.gateways import (
    GroupEventRepository,
    GroupMemberRepository,
    GroupRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    GroupEventItem,
    ListGroupEventsResponse,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class ListGroupEventsUseCase(TracedUseCase):
    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        user_repository: UserRepository,
        group_event_repository: GroupEventRepository,
    ):
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self.user_repository = user_repository
        self.group_event_repository = group_event_repository

    def execute(self, command: ListGroupEventsCommand) -> ListGroupEventsResponse:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if not AdminPermissionChecker.is_admin(command.requesting_user):
            if not self.group_member_repository.is_owner(command.group_id, command.requesting_user.user_id):
                raise UserNotOwnerOfGroupException(command.requesting_user.user_id, command.group_id)

        events = self.group_event_repository.list_events(
            group_id=command.group_id,
            event_types=command.event_types,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        event_items = []
        for event in events:
            enriched_event_data = dict(event["event_data"])

            target_user_id = enriched_event_data.get("user_id")
            if target_user_id:
                target_user = self.user_repository.get_by_id(UUID(target_user_id))
                if target_user:
                    enriched_event_data["user_email"] = target_user.email

            event_items.append(
                GroupEventItem(
                    event_id=str(event["event_id"]),
                    event_type=event["event_type"],
                    occurred_on=event["occurred_on"].isoformat()
                    if hasattr(event["occurred_on"], "isoformat")
                    else event["occurred_on"],
                    actor_user_id=str(event["actor_user_id"]),
                    actor_email=self._get_actor_email(event["actor_user_id"]),
                    event_data=enriched_event_data,
                )
            )

        return ListGroupEventsResponse(events=event_items)

    def _get_actor_email(self, actor_user_id: str) -> str | None:
        actor = self.user_repository.get_by_id(UUID(str(actor_user_id)))
        return actor.email if actor else None

from uuid import UUID

from password_management_context.application.commands import (
    ListPasswordEventsCommand,
)
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
    PasswordEventRepository,
)
from password_management_context.application.responses import (
    ListPasswordEventsResponse,
    PasswordEventItem,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)


class ListPasswordEventsUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        password_event_repository: PasswordEventRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.password_event_repository = password_event_repository

    def execute(self, command: ListPasswordEventsCommand) -> ListPasswordEventsResponse:
        password_entity = self.password_repository.get_by_id(command.password_id)
        if not password_entity:
            raise PasswordNotFoundError(command.password_id)

        # Check if user has access through their groups
        if not self._user_has_access_through_groups(
            command.user_id, command.password_id
        ):
            raise PasswordAccessDeniedError(command.user_id, command.password_id)

        # Fetch events from repository
        events = self.password_event_repository.list_events(
            password_id=command.password_id,
            event_types=command.event_types,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        # Convert to response DTOs
        event_items = [
            PasswordEventItem(
                event_id=str(event["event_id"]),
                event_type=event["event_type"],
                occurred_on=event["occurred_on"].isoformat()
                if hasattr(event["occurred_on"], "isoformat")
                else event["occurred_on"],
                actor_user_id=str(event["actor_user_id"]),
                event_data=event["event_data"],
            )
            for event in events
        ]

        return ListPasswordEventsResponse(events=event_items)

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user is owner or member of this group
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            # If user is in the group (owner or member), they can see events
            if is_user_owner or is_user_member:
                return True

        return False

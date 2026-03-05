from uuid import UUID

from password_management_context.application.commands import (
    ListPasswordEventsCommand,
)
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
    PasswordEventRepository,
    UserInfoGateway,
)
from password_management_context.application.responses import (
    ListPasswordEventsResponse,
    PasswordEventItem,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from shared_kernel.domain.services import AdminPermissionChecker


from shared_kernel.application.tracing import TracedUseCase


class ListPasswordEventsUseCase(TracedUseCase):
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        password_event_repository: PasswordEventRepository,
        user_info_gateway: UserInfoGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.password_event_repository = password_event_repository
        self.user_info_gateway = user_info_gateway

    def execute(self, command: ListPasswordEventsCommand) -> ListPasswordEventsResponse:
        password_entity = self.password_repository.get_by_id(command.password_id)
        if not password_entity:
            raise PasswordNotFoundError(command.password_id)

        if not AdminPermissionChecker.is_admin(command.requesting_user):
            if not self._user_has_access_through_groups(
                command.requesting_user.user_id, command.password_id
            ):
                raise PasswordAccessDeniedError(
                    command.requesting_user.user_id, command.password_id
                )

        events = self.password_event_repository.list_events(
            password_id=command.password_id,
            event_types=command.event_types,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        event_items = []
        for event in events:
            enriched_event_data = dict(event["event_data"])

            if (
                event["event_type"] == "PasswordSharedEvent"
                and "shared_with_group_id" in enriched_event_data
            ):
                group_id_str = enriched_event_data["shared_with_group_id"]
                if group_id_str:
                    group_name = self.user_info_gateway.get_group_name(
                        UUID(group_id_str)
                    )
                    if group_name:
                        enriched_event_data["shared_with_group_name"] = group_name

            if (
                event["event_type"] == "PasswordUnsharedEvent"
                and "unshared_with_group_id" in enriched_event_data
            ):
                group_id_str = enriched_event_data["unshared_with_group_id"]
                if group_id_str:
                    group_name = self.user_info_gateway.get_group_name(
                        UUID(group_id_str)
                    )
                    if group_name:
                        enriched_event_data["unshared_with_group_name"] = group_name

            event_items.append(
                PasswordEventItem(
                    event_id=str(event["event_id"]),
                    event_type=event["event_type"],
                    occurred_on=event["occurred_on"].isoformat()
                    if hasattr(event["occurred_on"], "isoformat")
                    else event["occurred_on"],
                    actor_user_id=str(event["actor_user_id"]),
                    actor_email=self.user_info_gateway.get_user_email(
                        UUID(str(event["actor_user_id"]))
                    ),
                    event_data=enriched_event_data,
                )
            )

        return ListPasswordEventsResponse(events=event_items)

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id in all_permissions:
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                return True

        return False

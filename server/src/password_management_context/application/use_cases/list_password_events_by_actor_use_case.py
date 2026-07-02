from password_management_context.application.commands import (
    ListPasswordEventsByActorCommand,
)
from password_management_context.application.gateways import (
    PasswordEventRepository,
)
from password_management_context.application.responses import (
    ListPasswordEventsByActorResponse,
    PasswordEventByActorItem,
)
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class ListPasswordEventsByActorUseCase(TracedUseCase):
    """List every password event performed by a given actor.

    Admin-only: lets an administrator browse the full action history
    (create, read, update, delete, share, unshare) of any user across
    all passwords.
    """

    def __init__(self, password_event_repository: PasswordEventRepository):
        self.password_event_repository = password_event_repository

    def execute(self, command: ListPasswordEventsByActorCommand) -> ListPasswordEventsByActorResponse:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "list password events by actor")

        events = self.password_event_repository.list_events_by_actor(
            actor_user_id=command.actor_user_id,
            event_types=command.event_types,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        return ListPasswordEventsByActorResponse(
            events=[
                PasswordEventByActorItem(
                    event_id=str(event["event_id"]),
                    event_type=event["event_type"],
                    occurred_on=event["occurred_on"].isoformat()
                    if hasattr(event["occurred_on"], "isoformat")
                    else event["occurred_on"],
                    password_id=str(event["password_id"]),
                    actor_user_id=str(event["actor_user_id"]),
                    event_data=event["event_data"],
                )
                for event in events
            ]
        )

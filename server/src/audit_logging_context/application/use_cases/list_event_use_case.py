from audit_logging_context.application.commands import ListEventCommand
from audit_logging_context.application.responses import ListEventResponse
from shared_kernel.domain.services import AdminPermissionChecker


class ListEventUseCase:
    def __init__(self, event_repository):
        self.event_repository = event_repository

    def execute(self, command: ListEventCommand) -> ListEventResponse:
        """List all audit events. Only administrators can access audit logs."""
        AdminPermissionChecker.ensure_admin(
            command.requesting_user, "view audit event logs"
        )
        events = self.event_repository.list_events()
        return ListEventResponse(events=events)

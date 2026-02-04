from uuid import UUID

from audit_logging_context.application.commands import ListEventCommand
from audit_logging_context.application.responses import ListEventResponse
from audit_logging_context.application.responses.list_event_response import EventDTO
from shared_kernel.domain.services import AdminPermissionChecker


class ListEventUseCase:
    def __init__(self, event_repository):
        self.event_repository = event_repository

    def execute(self, command: ListEventCommand) -> ListEventResponse:
        """List all audit events. Only administrators can access audit logs."""
        AdminPermissionChecker.ensure_admin(
            command.requesting_user, "view audit event logs"
        )
        events = self.event_repository.list_events(
            event_types=command.event_types,
            user_id=command.user_id,
            start_date=command.start_date,
            end_date=command.end_date,
        )

        # Convert domain events to DTOs with extracted user IDs
        event_dtos = []
        for event in events:
            event_user_id = self._extract_user_id(event)
            event_dtos.append(
                EventDTO(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    occurred_on=event.occurred_on,
                    priority=event.priority,
                    user_id=event_user_id,
                )
            )

        return ListEventResponse(events=event_dtos)

    def _extract_user_id(self, event) -> UUID | None:
        """Extract user ID from stored event - uses indexed column for efficiency"""
        # Use the extracted actor_user_id from StoredEvent (fast, from indexed column)
        if event.actor_user_id:
            return event.actor_user_id

        # Fallback: search in event_data for legacy events without extracted metadata
        for field in [
            "created_by_user_id",
            "updated_by_user_id",
            "deleted_by_user_id",
            "accessed_by_user_id",
            "user_id",
        ]:
            if field in event.event_data:
                try:
                    return UUID(event.event_data[field])
                except (ValueError, TypeError):
                    pass

        return None

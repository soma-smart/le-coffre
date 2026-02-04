# Standard library
import logging
from datetime import datetime
from uuid import UUID

# Third-party
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Local - application layer
from audit_logging_context.adapters.primary.fastapi.app_dependencies import (
    get_list_event_usecase,
)
from audit_logging_context.application.commands import ListEventCommand
from audit_logging_context.application.use_cases import ListEventUseCase

# Local - shared kernel
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

router = APIRouter(prefix="/events", tags=["Audit Logging"])


class EventData(BaseModel):
    event_id: UUID
    event_type: str
    occurred_on: datetime
    priority: str
    user_id: UUID | None = None

    model_config = {"from_attributes": True}


class ListEventResponse(BaseModel):
    events: list[EventData]


@router.get(
    "",
    response_model=ListEventResponse,
    status_code=200,
    summary="List all audit events",
)
def list_events(
    event_type: list[str] | None = Query(None, description="Filter by event types"),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    start_date: datetime | None = Query(
        None, description="Filter events from this date (inclusive)"
    ),
    end_date: datetime | None = Query(
        None, description="Filter events until this date (inclusive)"
    ),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListEventUseCase = Depends(get_list_event_usecase),
):
    """
    List all audit events from the system.

    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access audit logs
    - **event_type**: Optional list of event types to filter by (e.g., PasswordCreatedEvent, PasswordDeletedEvent)
    - **user_id**: Optional user ID to filter events related to a specific user
    - **start_date**: Optional start date to filter events (ISO 8601 format)
    - **end_date**: Optional end date to filter events (ISO 8601 format)

    Returns a list of all domain events that have been logged in the system.
    """
    try:
        # Execute use case with command
        authenticated_user = current_user.to_authenticated_user()
        command = ListEventCommand(
            requesting_user=authenticated_user,
            event_types=event_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        response = usecase.execute(command)

        # Convert DTOs to response format
        events_data = [
            EventData(
                event_id=event.event_id,
                event_type=event.event_type,
                occurred_on=event.occurred_on,
                priority=event.priority.value,
                user_id=event.user_id,
            )
            for event in response.events
        ]

        return ListEventResponse(events=events_data)

    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

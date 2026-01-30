from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
import logging

from audit_logging_context.adapters.primary.fastapi.app_dependencies import (
    get_list_event_usecase,
)
from audit_logging_context.application.use_cases import ListEventUseCase
from audit_logging_context.application.commands import ListEventCommand
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError

router = APIRouter(prefix="/events", tags=["Audit Logging"])


class EventData(BaseModel):
    event_id: UUID
    event_type: str
    occurred_on: datetime
    priority: str

    model_config = {"from_attributes": True}


class ListEventsResponse(BaseModel):
    events: list[EventData]


@router.get(
    "",
    response_model=ListEventsResponse,
    status_code=200,
    summary="List all audit events",
)
def list_events(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListEventUseCase = Depends(get_list_event_usecase),
):
    """
    List all audit events from the system.

    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access audit logs

    Returns a list of all domain events that have been logged in the system.
    """
    try:
        # Execute use case with command
        authenticated_user = current_user.to_authenticated_user()
        command = ListEventCommand(requesting_user=authenticated_user)
        response = usecase.execute(command)

        # Convert domain events to response format
        events_data = [
            EventData(
                event_id=event.event_id,
                event_type=event.event_type,
                occurred_on=event.occurred_on,
                priority=event.priority.value,
            )
            for event in response.events
        ]

        return ListEventsResponse(events=events_data)

    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_group_events_usecase,
)
from identity_access_management_context.application.commands import (
    ListGroupEventsCommand,
)
from identity_access_management_context.application.use_cases import (
    ListGroupEventsUseCase,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Group Management"])


class GroupEventResponse(BaseModel):
    event_id: str
    event_type: str
    occurred_on: str
    actor_user_id: str
    actor_email: str | None
    event_data: dict


class ListGroupEventsResponse(BaseModel):
    events: list[GroupEventResponse]


@router.get(
    "/{group_id}/events",
    response_model=ListGroupEventsResponse,
    status_code=200,
    summary="List membership events for a group",
)
def list_group_events(
    group_id: UUID,
    event_type: list[str] | None = Query(None, description="Filter by event types"),
    start_date: datetime | None = Query(None, description="Filter events from this date (inclusive)"),
    end_date: datetime | None = Query(None, description="Filter events until this date (inclusive)"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListGroupEventsUseCase = Depends(get_list_group_events_usecase),
):
    """
    Retrieve the membership event history for a group: members added, owners
    added/promoted, and members removed.

    Only group owners and admins can list events for a group.

    - **group_id**: The ID of the group
    - **event_type**: Optional filter by event types
    - **start_date**: Optional filter from this date
    - **end_date**: Optional filter until this date
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        command = ListGroupEventsCommand(
            group_id=group_id,
            requesting_user=current_user.to_authenticated_user(),
            event_types=event_type,
            start_date=start_date,
            end_date=end_date,
        )
        response = usecase.execute(command)

        return ListGroupEventsResponse(
            events=[
                GroupEventResponse(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    occurred_on=event.occurred_on,
                    actor_user_id=event.actor_user_id,
                    actor_email=event.actor_email,
                    event_data=event.event_data,
                )
                for event in response.events
            ]
        )
    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in list group events")
        raise HTTPException(status_code=500, detail="Internal server error") from e

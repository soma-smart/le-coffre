import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_password_events_usecase,
)
from password_management_context.application.commands import (
    ListPasswordEventsCommand,
)
from password_management_context.application.use_cases import (
    ListPasswordEventsUseCase,
)
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class PasswordEventResponse(BaseModel):
    event_id: str
    event_type: str
    occurred_on: str
    actor_user_id: str
    actor_email: str | None
    event_data: dict


class ListPasswordEventsResponse(BaseModel):
    events: list[PasswordEventResponse]


@router.get(
    "/{password_id}/events",
    response_model=ListPasswordEventsResponse,
    status_code=200,
    summary="List events for a password",
)
def list_password_events(
    password_id: UUID,
    event_type: list[str] | None = Query(None, description="Filter by event types"),  # noqa: B008
    start_date: datetime | None = Query(None, description="Filter events from this date (inclusive)"),  # noqa: B008
    end_date: datetime | None = Query(None, description="Filter events until this date (inclusive)"),  # noqa: B008
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: ListPasswordEventsUseCase = Depends(get_list_password_events_usecase),  # noqa: B008
):
    """
    Retrieve the event history for a specific password.

    Admins can list events for any password. Owners and members can list events
    for passwords they have access to through their groups.

    - **password_id**: The ID of the password
    - **event_type**: Optional filter by event types
    - **start_date**: Optional filter from this date
    - **end_date**: Optional filter until this date
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        command = ListPasswordEventsCommand(
            password_id=password_id,
            requesting_user=current_user.to_authenticated_user(),
            event_types=event_type,
            start_date=start_date,
            end_date=end_date,
        )
        response = usecase.execute(command)

        return ListPasswordEventsResponse(
            events=[
                PasswordEventResponse(
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
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PasswordAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error") from e

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_password_events_by_actor_usecase,
)
from password_management_context.application.commands import (
    ListPasswordEventsByActorCommand,
)
from password_management_context.application.use_cases import (
    ListPasswordEventsByActorUseCase,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["Password Management"])


class PasswordEventByActorResponseItem(BaseModel):
    event_id: str
    event_type: str
    occurred_on: str
    password_id: str
    actor_user_id: str
    event_data: dict


class ListPasswordEventsByActorResponseSchema(BaseModel):
    events: list[PasswordEventByActorResponseItem]


@router.get(
    "/{user_id}/password-events",
    response_model=ListPasswordEventsByActorResponseSchema,
    status_code=200,
    summary="List all password actions performed by a user (admin only)",
)
def list_password_events_by_actor(
    user_id: UUID,
    event_type: list[str] | None = Query(None, description="Filter by event types"),
    start_date: datetime | None = Query(None, description="Filter events from this date (inclusive)"),
    end_date: datetime | None = Query(None, description="Filter events until this date (inclusive)"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListPasswordEventsByActorUseCase = Depends(get_list_password_events_by_actor_usecase),
):
    """
    Retrieve the full action history (create, read, update, delete, share, unshare)
    performed by a given user across **all** passwords.

    - **user_id**: The ID of the user whose actions are being audited
    - **event_type**: Optional filter by event types
    - **start_date**: Optional filter from this date
    - **end_date**: Optional filter until this date
    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access this endpoint
    """
    try:
        command = ListPasswordEventsByActorCommand(
            actor_user_id=user_id,
            requesting_user=current_user.to_authenticated_user(),
            event_types=event_type,
            start_date=start_date,
            end_date=end_date,
        )
        response = usecase.execute(command)

        return ListPasswordEventsByActorResponseSchema(
            events=[
                PasswordEventByActorResponseItem(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    occurred_on=event.occurred_on,
                    password_id=event.password_id,
                    actor_user_id=event.actor_user_id,
                    event_data=event.event_data,
                )
                for event in response.events
            ]
        )
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in list_password_events_by_actor")
        raise HTTPException(status_code=500, detail="Internal server error") from e

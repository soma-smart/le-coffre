import logging
from uuid import UUID

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from notification_context.adapters.primary.fastapi.app_dependencies import get_subscribe_to_one_time_link_usecase
from notification_context.application.commands import SubscribeToOneTimeLinkCommand
from notification_context.application.use_cases import SubscribeToOneTimeLinkUseCase
from notification_context.domain.exceptions import OneTimeLinkNoLongerActiveError, OneTimeLinkNotFoundError
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class OneTimeLinkSubscriptionRequest(BaseModel):
    notify_on_read: bool
    notify_on_expiry: bool


class OneTimeLinkSubscriptionResponse(BaseModel):
    link_id: UUID
    notify_on_read: bool
    notify_on_expiry: bool


@router.put(
    "/one-time-links/{link_id}",
    response_model=OneTimeLinkSubscriptionResponse,
    status_code=200,
    summary="Choose the emails to receive about one of your one-time links",
)
def subscribe_to_one_time_link(
    link_id: UUID,
    request: OneTimeLinkSubscriptionRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: SubscribeToOneTimeLinkUseCase = Depends(get_subscribe_to_one_time_link_usecase),
):
    """
    Only the creator of the link can follow it, and only while it can still be read.

    - **notify_on_read**: email when the link is opened
    - **notify_on_expiry**: email if the link expires without having been opened

    Setting both to false stops following the link.
    """
    try:
        subscription = usecase.execute(
            SubscribeToOneTimeLinkCommand(
                link_id=link_id,
                user_id=current_user.user_id,
                notify_on_read=request.notify_on_read,
                notify_on_expiry=request.notify_on_expiry,
            )
        )
        return OneTimeLinkSubscriptionResponse(
            link_id=subscription.link_id,
            notify_on_read=subscription.notify_on_read,
            notify_on_expiry=subscription.notify_on_expiry,
        )
    except OneTimeLinkNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OneTimeLinkNoLongerActiveError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error subscribing to a one-time link")
        raise HTTPException(status_code=500, detail="Internal server error") from e

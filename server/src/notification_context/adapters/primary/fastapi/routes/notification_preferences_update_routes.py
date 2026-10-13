import logging

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from notification_context.adapters.primary.fastapi.app_dependencies import (
    get_update_notification_preferences_usecase,
)
from notification_context.application.commands import UpdateNotificationPreferencesCommand
from notification_context.application.use_cases import UpdateNotificationPreferencesUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

from ._notification_preferences_response import NotificationPreferencesResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class UpdateNotificationPreferencesRequest(BaseModel):
    notify_on_vault_lock: bool
    notify_on_vault_unlock: bool


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=200,
    summary="Update the current user's notification preferences",
)
def update_notification_preferences(
    request: UpdateNotificationPreferencesRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdateNotificationPreferencesUseCase = Depends(get_update_notification_preferences_usecase),
):
    """Replace the authenticated user's notification preferences."""
    try:
        command = UpdateNotificationPreferencesCommand(
            user_id=current_user.user_id,
            notify_on_vault_lock=request.notify_on_vault_lock,
            notify_on_vault_unlock=request.notify_on_vault_unlock,
        )
        return NotificationPreferencesResponse.from_preferences(usecase.execute(command))
    except Exception as e:
        logger.exception("Unexpected error updating notification preferences")
        raise HTTPException(status_code=500, detail="Internal server error") from e

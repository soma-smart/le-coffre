import logging

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from notification_context.adapters.primary.fastapi.app_dependencies import (
    get_get_notification_preferences_usecase,
    get_update_notification_preferences_usecase,
)
from notification_context.application.commands import (
    GetNotificationPreferencesCommand,
    UpdateNotificationPreferencesCommand,
)
from notification_context.application.use_cases import (
    GetNotificationPreferencesUseCase,
    UpdateNotificationPreferencesUseCase,
)
from notification_context.domain.entities import NotificationPreferences
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationPreferencesResponse(BaseModel):
    notify_on_vault_lock: bool
    notify_on_vault_unlock: bool


class UpdateNotificationPreferencesRequest(BaseModel):
    notify_on_vault_lock: bool
    notify_on_vault_unlock: bool


def _to_response(preferences: NotificationPreferences) -> NotificationPreferencesResponse:
    return NotificationPreferencesResponse(
        notify_on_vault_lock=preferences.notify_on_vault_lock,
        notify_on_vault_unlock=preferences.notify_on_vault_unlock,
    )


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    status_code=200,
    summary="Get the current user's notification preferences",
)
def get_notification_preferences(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetNotificationPreferencesUseCase = Depends(get_get_notification_preferences_usecase),
):
    """
    Which optional emails the authenticated user receives. Everything is off until
    the user turns it on.

    - **notify_on_vault_lock**: email when the vault gets locked (by an admin, or by a server restart)
    - **notify_on_vault_unlock**: email when the vault gets unlocked
    """
    try:
        return _to_response(usecase.execute(GetNotificationPreferencesCommand(user_id=current_user.user_id)))
    except Exception as e:
        logger.exception("Unexpected error getting notification preferences")
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
        return _to_response(usecase.execute(command))
    except Exception as e:
        logger.exception("Unexpected error updating notification preferences")
        raise HTTPException(status_code=500, detail="Internal server error") from e

import logging

from fastapi import APIRouter, Depends, HTTPException
from notification_context.adapters.primary.fastapi.app_dependencies import get_get_notification_preferences_usecase
from notification_context.application.commands import GetNotificationPreferencesCommand
from notification_context.application.use_cases import GetNotificationPreferencesUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

from ._notification_preferences_response import NotificationPreferencesResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


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
        preferences = usecase.execute(GetNotificationPreferencesCommand(user_id=current_user.user_id))
        return NotificationPreferencesResponse.from_preferences(preferences)
    except Exception as e:
        logger.exception("Unexpected error getting notification preferences")
        raise HTTPException(status_code=500, detail="Internal server error") from e

import logging

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import get_admin_stat_usecase
from identity_access_management_context.application.commands import GetAdminStatCommand
from identity_access_management_context.application.use_cases.get_admin_stat_use_case import GetAdminStatUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/stats",
    status_code=200,
    summary="Get admin statistics",
)
def get_admin_stats(usecase: GetAdminStatUseCase = Depends(get_admin_stat_usecase)):
    """
    Retrieve administrative statistics about the system.

    - **Authentication**: Requires authentication via access_token cookie

    Returns:
    - groupCount: Total number of groups in the system
    - userCount: Total number of users in the system
    - passwordCount: Total number of user passwords in the system
    """
    try:
        command = GetAdminStatCommand()
        response = usecase.execute(command)
        # The actual implementation will be done in the use case and gateway layers.
        # This is just a placeholder to define the route and response structure.
        return response
    except Exception as e:
        logger.exception("Unexpected error in get admin stats")
        raise HTTPException(status_code=500, detail="Internal server error") from e

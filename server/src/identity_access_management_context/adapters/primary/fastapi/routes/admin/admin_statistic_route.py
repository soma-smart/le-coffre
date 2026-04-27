import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_statistic_for_admin_usecase,
)
from identity_access_management_context.application.commands import GetStatisticForAdminCommand
from identity_access_management_context.application.use_cases import GetStatisticForAdminUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


class StatisticForAdminResponse(BaseModel):
    user_count: int
    group_count: int


@router.get(
    "/statistics",
    response_model=StatisticForAdminResponse,
    status_code=200,
    summary="Get statistics for admin",
)
def get_statistic_for_admin(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetStatisticForAdminUseCase = Depends(get_statistic_for_admin_usecase),
):
    """
    Retrieve global statistics (number of users and groups).

    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access this endpoint

    Returns the total count of users and groups in the system.
    """
    try:
        command = GetStatisticForAdminCommand(requesting_user=current_user.to_authenticated_user())
        result = usecase.execute(command)

        return StatisticForAdminResponse(
            user_count=result.user_count,
            group_count=result.group_count,
        )
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get statistic for admin")
        raise HTTPException(status_code=500, detail="Internal server error") from e

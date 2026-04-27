import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_password_statistic_for_admin_usecase,
)
from password_management_context.application.commands import GetPasswordStatisticForAdminCommand
from password_management_context.application.use_cases import GetPasswordStatisticForAdminUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class PasswordStatisticForAdminResponse(BaseModel):
    password_count: int


@router.get(
    "/admin/statistics",
    response_model=PasswordStatisticForAdminResponse,
    status_code=200,
    summary="Get password statistics for admin",
)
def get_password_statistic_for_admin(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetPasswordStatisticForAdminUseCase = Depends(get_password_statistic_for_admin_usecase),
):
    """
    Retrieve password statistics.

    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can access this endpoint

    Returns the total count of passwords in the system.
    """
    try:
        command = GetPasswordStatisticForAdminCommand(requesting_user=current_user.to_authenticated_user())
        result = usecase.execute(command)

        return PasswordStatisticForAdminResponse(
            password_count=result.password_count,
        )
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get password statistic for admin")
        raise HTTPException(status_code=500, detail="Internal server error") from e

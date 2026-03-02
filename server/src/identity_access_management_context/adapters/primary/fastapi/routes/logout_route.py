import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_logout_usecase,
)
from identity_access_management_context.application.use_cases import LogoutUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LogoutResponse(BaseModel):
    message: str


@router.post(
    "/logout",
    status_code=200,
    response_model=LogoutResponse,
    summary="Logout the current user",
)
async def logout(
    response: Response,
    current_user: ValidatedUser = Depends(get_current_user),
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    usecase: LogoutUseCase = Depends(get_logout_usecase),
):
    """
    Logout the current user.

    - **Authentication**: Requires authentication via access_token cookie
    - Revokes the refresh token server-side so it can no longer be used
    - Clears the access_token and refresh_token cookies from the client

    **Responses**:
    - **200**: Successfully logged out
    - **401**: Not authenticated
    - **500**: Internal server error
    """
    try:
        await usecase.execute(
            current_user=current_user,
            refresh_token=refresh_token_cookie,
        )

        # Clear both auth cookies on the client
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("logged_in")

        return LogoutResponse(message="Logged out successfully")
    except Exception as e:
        logger.exception("Unexpected error during logout")
        raise HTTPException(status_code=500, detail="Internal server error")

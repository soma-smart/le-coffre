from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from config import get_cookie_secure_setting
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_logout_usecase,
)
from identity_access_management_context.application.commands import LogoutCommand
from identity_access_management_context.application.use_cases import LogoutUseCase

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LogoutResponse(BaseModel):
    message: str


@router.post(
    "/logout",
    status_code=200,
    response_model=LogoutResponse,
    summary="Logout current session",
)
def logout(
    response: Response,
    access_token_cookie: str | None = Cookie(None, alias="access_token"),
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
    usecase: LogoutUseCase = Depends(get_logout_usecase),
):
    """
    Logout the current browser session.

    - **access_token**: Optional access token cookie to revoke
    - **refresh_token**: Optional refresh token cookie to revoke
    - **Authentication**: Clears cookies even if tokens are already missing or expired
    """
    usecase.execute(
        LogoutCommand(
            access_token=access_token_cookie,
            refresh_token=refresh_token_cookie,
        )
    )

    is_secure = get_cookie_secure_setting()
    response.delete_cookie("access_token", secure=is_secure, samesite="strict")
    response.delete_cookie("refresh_token", secure=is_secure, samesite="strict")
    response.delete_cookie("logged_in", secure=is_secure, samesite="strict")

    return LogoutResponse(message="Logout successful")

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from config import get_cookie_secure_setting, get_jwt_access_token_expiration_seconds
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_refresh_access_token_usecase,
)
from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.application.use_cases import (
    RefreshAccessTokenUseCase,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshAccessTokenResponse(BaseModel):
    message: str


@router.post(
    "/refresh-token",
    status_code=200,
    response_model=RefreshAccessTokenResponse,
    summary="Refresh access token",
)
async def refresh_access_token(
    response: Response,
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
    usecase: RefreshAccessTokenUseCase = Depends(get_refresh_access_token_usecase),
):
    """
    Refresh access token using a refresh token.

    This endpoint allows clients to obtain a new access token using a valid refresh token.
    The refresh token must be provided as an HTTP-only cookie.

    Sets a new access token in an HTTP-only secure cookie.
    The refresh token remains valid and unchanged.

    **Responses**:
    - **200**: Successfully refreshed access token
    - **400**: Invalid or expired refresh token, or user no longer exists
    - **500**: Internal server error
    """
    try:
        if not refresh_token_cookie:
            raise HTTPException(
                status_code=400,
                detail="Refresh token cookie is required",
            )

        command = RefreshAccessTokenCommand(refresh_token=refresh_token_cookie)
        # Set new access token in HTTP-only secure cookie
        result = await usecase.execute(command)
        is_secure = get_cookie_secure_setting()
        access_token_max_age = get_jwt_access_token_expiration_seconds()
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            secure=is_secure,
            samesite="strict",
            max_age=access_token_max_age,
        )
        # Renew the non-httpOnly auth flag so the frontend can still detect the
        # active session (it expires at the same time as the access token).
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,
            secure=is_secure,
            samesite="strict",
            max_age=access_token_max_age,
        )

        return RefreshAccessTokenResponse(message="Access token refreshed successfully")
    except InvalidRefreshTokenException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in refresh access token")
        raise HTTPException(status_code=500, detail="Internal server error") from e

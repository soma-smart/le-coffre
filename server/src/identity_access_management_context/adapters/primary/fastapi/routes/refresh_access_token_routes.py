from fastapi import APIRouter, HTTPException, Depends, Response, Cookie
from pydantic import BaseModel
import logging
from typing import Optional

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_refresh_access_token_usecase,
)
from identity_access_management_context.application.use_cases import (
    RefreshAccessTokenUseCase,
)
from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from config import get_cookie_secure_setting, get_jwt_access_token_expiration_minutes

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
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
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
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=get_jwt_access_token_expiration_minutes()
            * 60,  # Convert minutes to seconds
        )

        return RefreshAccessTokenResponse(message="Access token refreshed successfully")
    except InvalidRefreshTokenException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error refreshing access token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

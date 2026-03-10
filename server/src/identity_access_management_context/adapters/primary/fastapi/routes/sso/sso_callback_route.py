from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from config import (
    get_cookie_secure_setting,
    get_jwt_access_token_expiration_minutes,
    get_jwt_refresh_token_expiration_days,
)
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_sso_login_usecase,
)
from identity_access_management_context.application.commands.sso_login_command import (
    SsoLoginCommand,
)
from identity_access_management_context.application.use_cases import SsoLoginUseCase
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException

router = APIRouter(prefix="/auth", tags=["Authentication"])


class SsoUserInfo(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    is_new_user: bool


class SsoCallbackResponse(BaseModel):
    message: str
    user: SsoUserInfo


@router.get(
    "/sso/callback",
    status_code=200,
    response_model=SsoCallbackResponse,
    summary="SSO callback endpoint",
)
async def sso_callback(
    response: Response,
    code: str = Query(..., description="Authorization code from SSO provider"),
    state: str = Query(None, description="State parameter for CSRF protection"),
    usecase: SsoLoginUseCase = Depends(get_sso_login_usecase),
):
    """
    SSO callback endpoint.

    This endpoint is called by the SSO provider after the user has authorized the application.
    It exchanges the authorization code for an access token and signs the user in.

    - **code**: The authorization code provided by the SSO provider
    - **state**: (Optional) State parameter for CSRF protection

    Returns user information and sets HTTP-only secure cookies with JWT tokens.
    """
    try:
        command = SsoLoginCommand(code=code)
        result = await usecase.execute(command)

        # Set JWT tokens in HTTP-only cookies (not accessible by JavaScript)
        is_secure = get_cookie_secure_setting()

        response.set_cookie(
            key="access_token",
            value=result.jwt_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="lax",  # CSRF protection
            max_age=get_jwt_access_token_expiration_minutes() * 60,  # Convert minutes to seconds
        )

        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="lax",
            max_age=get_jwt_refresh_token_expiration_days() * 86400,  # Convert days to seconds
        )

        # Set a non-httpOnly cookie that frontend can read to check auth status
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,  # JavaScript can read this
            secure=is_secure,
            samesite="lax",
            max_age=get_jwt_access_token_expiration_minutes() * 60,
        )

        return SsoCallbackResponse(
            message="SSO authentication successful",
            user=SsoUserInfo(
                user_id=result.user_id,
                email=result.email,
                display_name=result.display_name,
                is_new_user=result.is_new_user,
            ),
        )
    except InvalidSsoCodeException as e:
        raise HTTPException(status_code=400, detail=f"SSO authentication failed: {str(e)}") from e

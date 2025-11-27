from fastapi import APIRouter, HTTPException, Depends, Response
import logging
from pydantic import BaseModel
from uuid import UUID

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_admin_login_usecase,
)
from identity_access_management_context.application.use_cases import AdminLoginUseCase
from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)
from config import (
    get_cookie_secure_setting,
    get_jwt_access_token_expiration_minutes,
    get_jwt_refresh_token_expiration_days,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    admin_id: UUID
    email: str
    message: str


@router.post(
    "/login",
    status_code=200,
    response_model=AdminLoginResponse,
    summary="Login admin user",
)
async def admin_login(
    request: AdminLoginRequest,
    response: Response,
    usecase: AdminLoginUseCase = Depends(get_admin_login_usecase),
):
    """
    Login an admin user.

    - **email**: Email address of the admin user
    - **password**: Password of the admin user

    Returns admin information and sets an HTTP-only secure cookie with the JWT token.
    """
    try:
        command = AdminLoginCommand(
            email=request.email,
            password=request.password,
        )

        result = await usecase.execute(command)

        # Set JWT token in HTTP-only secure cookie
        is_secure = get_cookie_secure_setting()
        response.set_cookie(
            key="access_token",
            value=result.jwt_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="lax",  # CSRF protection
            max_age=get_jwt_access_token_expiration_minutes()
            * 60,  # Convert minutes to seconds
        )

        # Also set refresh token in cookie
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="lax",
            max_age=get_jwt_refresh_token_expiration_days()
            * 86400,  # Convert days to seconds
        )

        return AdminLoginResponse(
            admin_id=result.admin_id,
            email=result.email,
            message="Login successful",
        )

    except (InvalidCredentialsException, AdminNotFoundException) as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

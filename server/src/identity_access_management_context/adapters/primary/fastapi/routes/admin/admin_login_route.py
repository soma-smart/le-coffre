import logging
from uuid import UUID

from config import (
    get_cookie_secure_setting,
    get_jwt_access_token_expiration_seconds,
    get_jwt_refresh_token_expiration_seconds,
)
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from security import InMemoryLoginLockout

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_login_lockout,
    get_password_login_usecase,
)
from identity_access_management_context.adapters.primary.fastapi.schemas.admin_login_schema import (
    AdminLoginRequest,
)
from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.use_cases import (
    PasswordLoginUseCase,
)
from identity_access_management_context.domain.exceptions import (
    AdminNotFoundException,
    InvalidCredentialsException,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    usecase: PasswordLoginUseCase = Depends(get_password_login_usecase),
    lockout: InMemoryLoginLockout = Depends(get_login_lockout),
):
    """
    Login an admin user.

    - **email**: Email address of the admin user
    - **password**: Password of the admin user

    Returns admin information and sets an HTTP-only secure cookie with the JWT token.
    """
    locked, retry_after = lockout.is_locked(request.email)
    if locked:
        raise HTTPException(
            status_code=401,
            detail="Account temporarily locked due to too many failed login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    command = AdminLoginCommand(
        email=request.email,
        password=request.password,
    )

    try:
        result = await usecase.execute(command)
    except (InvalidCredentialsException, AdminNotFoundException) as e:
        lockout.record_failure(command.email)
        raise HTTPException(status_code=401, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in admin login")
        raise HTTPException(status_code=500, detail="Internal server error") from e

    is_secure = get_cookie_secure_setting()
    response.set_cookie(
        key="access_token",
        value=result.jwt_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=get_jwt_access_token_expiration_seconds(),
    )
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=get_jwt_refresh_token_expiration_seconds(),
    )
    response.set_cookie(
        key="logged_in",
        value="true",
        httponly=False,
        secure=is_secure,
        samesite="strict",
        max_age=get_jwt_access_token_expiration_seconds(),
    )

    lockout.record_success(command.email)

    return AdminLoginResponse(
        admin_id=result.admin_id,
        email=result.email,
        message="Login successful",
    )

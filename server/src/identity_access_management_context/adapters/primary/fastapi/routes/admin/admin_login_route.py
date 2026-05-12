import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from config import (
    get_cookie_secure_setting,
    get_jwt_access_token_expiration_seconds,
    get_jwt_refresh_token_expiration_seconds,
)
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_password_login_usecase,
)
from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.use_cases import (
    PasswordLoginUseCase,
)
from identity_access_management_context.domain.exceptions import (
    AccountLockedException,
    AdminNotFoundException,
    InvalidCredentialsException,
)

logger = logging.getLogger(__name__)

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
def admin_login(
    request: AdminLoginRequest,
    response: Response,
    usecase: PasswordLoginUseCase = Depends(get_password_login_usecase),
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

        result = usecase.execute(command)

        # Set JWT token in HTTP-only secure cookie
        is_secure = get_cookie_secure_setting()
        response.set_cookie(
            key="access_token",
            value=result.jwt_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="strict",  # CSRF protection
            max_age=get_jwt_access_token_expiration_seconds(),
        )

        # Also set refresh token in cookie
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=is_secure,  # HTTPS only in production
            samesite="strict",
            max_age=get_jwt_refresh_token_expiration_seconds(),
        )

        # Set a non-httpOnly cookie that frontend can read to check auth status
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,  # JavaScript can read this
            secure=is_secure,
            samesite="strict",
            max_age=get_jwt_access_token_expiration_seconds(),
        )

        return AdminLoginResponse(
            admin_id=result.admin_id,
            email=result.email,
            message="Login successful",
        )

    # Every authentication-failure path returns the exact same 401 body so an
    # attacker cannot enumerate valid emails by reading response text. The
    # lockout signal is carried exclusively by the Retry-After header, which is
    # not itself an oracle: the lockout gateway records failures for any email
    # (valid or not), so the header appears after N attempts regardless.
    except AccountLockedException as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"Retry-After": str(e.retry_after_seconds)},
        ) from e
    except (InvalidCredentialsException, AdminNotFoundException) as e:
        raise HTTPException(status_code=401, detail="Invalid credentials") from e
    except Exception as e:
        logger.exception("Unexpected error in admin login")
        raise HTTPException(status_code=500, detail="Internal server error") from e

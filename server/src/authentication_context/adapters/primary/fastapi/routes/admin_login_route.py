from fastapi import APIRouter, HTTPException, Depends
import logging
from pydantic import BaseModel
from uuid import UUID

from authentication_context.adapters.primary.fastapi.app_dependencies import (
    get_admin_login_usecase,
)
from authentication_context.application.use_cases import AdminLoginUseCase
from authentication_context.application.commands import AdminLoginCommand
from authentication_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    jwt_token: str
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
    usecase: AdminLoginUseCase = Depends(get_admin_login_usecase),
):
    """
    Login an admin user.

    - **email**: Email address of the admin user
    - **password**: Password of the admin user

    Returns a JWT token and admin information.
    """
    try:
        command = AdminLoginCommand(
            email=request.email,
            password=request.password,
        )

        response = await usecase.execute(command)

        return AdminLoginResponse(
            jwt_token=response.jwt_token,
            admin_id=response.admin_id,
            email=response.email,
            message="Login successful",
        )

    except (InvalidCredentialsException, AdminNotFoundException) as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

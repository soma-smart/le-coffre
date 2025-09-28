from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID, uuid4
import logging
from pydantic import BaseModel

from authentication_context.adapters.primary.fastapi.app_dependencies import (
    get_register_admin_usecase,
)
from authentication_context.application.use_cases import (
    RegisterAdminWithPasswordUseCase,
)
from authentication_context.application.commands import RegisterAdminWithPasswordCommand
from authentication_context.domain.exceptions import (
    AdminAlreadyExistsException,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterAdminRequest(BaseModel):
    email: str
    password: str
    display_name: str


class RegisterAdminResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    message: str


@router.post(
    "/register-admin",
    status_code=201,
    response_model=RegisterAdminResponse,
    summary="Register the first admin user",
)
async def register_admin(
    request: RegisterAdminRequest,
    usecase: RegisterAdminWithPasswordUseCase = Depends(get_register_admin_usecase),
):
    """
    Register the first admin user for the system.

    - **email**: Email address for the admin user
    - **password**: Password for the admin user (will be hashed)
    - **display_name**: Display name for the admin user

    Returns the created admin information with generated ID.
    """
    try:
        admin_id = uuid4()

        command = RegisterAdminWithPasswordCommand(
            id=admin_id,
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )

        created_admin_id = await usecase.execute(command)

        return RegisterAdminResponse(
            id=created_admin_id,
            email=request.email,
            display_name=request.display_name,
            message="Admin registered successfully",
        )

    except AdminAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

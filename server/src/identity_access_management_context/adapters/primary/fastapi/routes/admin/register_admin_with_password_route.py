import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_register_admin_usecase,
)
from identity_access_management_context.application.commands import RegisterAdminWithPasswordCommand
from identity_access_management_context.application.use_cases import (
    RegisterAdminWithPasswordUseCase,
)
from identity_access_management_context.domain.exceptions import (
    AdminAlreadyExistsException,
)

logger = logging.getLogger(__name__)

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
def register_admin(
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

        created_admin_id = usecase.execute(command)

        return RegisterAdminResponse(
            id=created_admin_id,
            email=request.email,
            display_name=request.display_name,
            message="Admin registered successfully",
        )

    except AdminAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in register admin")
        raise HTTPException(status_code=500, detail="Internal server error") from e

from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID, uuid4
import logging
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_register_admin_usecase,
)
from identity_access_management_context.application.use_cases import (
    RegisterWithPasswordUseCase,
)
from identity_access_management_context.application.commands import (
    RegisterWithPasswordCommand,
)
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsException,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterUserRequest(BaseModel):
    email: str
    password: str
    display_name: str


class RegisterUserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    message: str


@router.post(
    "/register",
    status_code=201,
    response_model=RegisterUserResponse,
    summary="Register users",
)
async def register_user(
    request: RegisterUserRequest,
    usecase: RegisterWithPasswordUseCase = Depends(get_register_admin_usecase),
):
    """
    Register the first user for the system.

    - **email**: Email address for the user
    - **password**: Password for the user (will be hashed)
    - **display_name**: Display name for the user
    Returns the created user information with generated ID.
    """
    try:
        user_id = uuid4()

        command = RegisterWithPasswordCommand(
            id=user_id,
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )

        created_user_id = await usecase.execute(command)

        return RegisterUserResponse(
            id=created_user_id,
            email=request.email,
            display_name=request.display_name,
            message="User registered successfully",
        )

    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

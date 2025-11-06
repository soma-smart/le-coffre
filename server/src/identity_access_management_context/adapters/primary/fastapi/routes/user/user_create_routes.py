from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID, uuid4
import logging
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_user_usecase,
)
from identity_access_management_context.application.use_cases import CreateUserUseCase
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsError,
)

router = APIRouter(prefix="/users", tags=["User Management"])


class CreateUserRequest(BaseModel):
    username: str
    email: str
    name: str


class CreateUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    message: str


@router.post(
    "/",
    status_code=201,
    response_model=CreateUserResponse,
    summary="Create a new user",
)
def create_user(
    request: CreateUserRequest,
    usecase: CreateUserUseCase = Depends(get_create_user_usecase),
):
    """
    Create a new user.

    - **username**: Username for the new user
    - **email**: Email address for the new user
    - **password**: Password for the new user (will be hashed)

    Returns the created user information with generated ID.
    """
    try:
        user_id = uuid4()

        command = CreateUserCommand(
            id=user_id,
            username=request.username,
            email=request.email,
            name=request.name,
        )

        created_user_id = usecase.execute(command)

        return CreateUserResponse(
            id=created_user_id,
            username=request.username,
            email=request.email,
            message="User created successfully",
        )

    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_user_usecase,
)
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.use_cases import CreateUserUseCase
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
    UserAlreadyExistsException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.domain.exceptions import AccessDeniedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


class CreateUserRequest(BaseModel):
    username: str
    email: str
    name: str
    password: str


class CreateUserResponse(BaseModel):
    id: UUID


@router.post(
    "/",
    response_model=CreateUserResponse,
    status_code=201,
    summary="Create a new user",
)
def create_user(
    request_body: CreateUserRequest,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: CreateUserUseCase = Depends(get_create_user_usecase),  # noqa: B008
):
    """
    Create a new user with password authentication.

    - **username**: Unique username for the user
    - **email**: User's email address
    - **name**: User's display name
    - **password**: Password for the user account
    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Admin only
    """
    try:
        command = CreateUserCommand(
            requesting_user=current_user.to_authenticated_user(),
            id=uuid4(),
            username=request_body.username,
            email=request_body.email,
            name=request_body.name,
            password=request_body.password,
        )
        user_id = usecase.execute(command)

        return CreateUserResponse(id=user_id)
    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in create user")
        raise HTTPException(status_code=500, detail="Internal server error") from e

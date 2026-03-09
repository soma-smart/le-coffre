import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_password_usecase,
)
from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.application.use_cases import CreatePasswordUseCase
from password_management_context.domain.exceptions import PasswordManagementDomainError
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.domain.exceptions import AccessDeniedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class CreatePasswordRequest(BaseModel):
    name: str
    password: str
    folder: str | None = None
    login: str | None = None
    url: str | None = None
    group_id: str


class CreatePasswordResponse(BaseModel):
    id: UUID


@router.post(
    "/",
    response_model=CreatePasswordResponse,
    status_code=201,
    summary="Create a new password",
)
def create_password(
    request_body: CreatePasswordRequest,
    request: Request,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: CreatePasswordUseCase = Depends(get_create_password_usecase),  # noqa: B008
):
    """
    Create a new password entry.

    - **name**: Name/title for the password entry
    - **password**: The actual password to store (will be encrypted)
    - **folder**: Optional folder to organize the password
    - **login**: Optional login or username associated with the password
    - **url**: Optional URL associated with the password entry
    - **group_id**: Optional group ID. If not provided, uses the user's personal group
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        password_id = uuid4()
        command = CreatePasswordCommand(
            id=password_id,
            user_id=current_user.user_id,
            group_id=UUID(request_body.group_id),
            name=request_body.name,
            decrypted_password=request_body.password,
            folder=request_body.folder,
            login=request_body.login,
            url=request_body.url,
        )

        created_password_id = usecase.execute(command)

        return CreatePasswordResponse(id=created_password_id)
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in create password")
        raise HTTPException(status_code=500, detail="Internal server error") from e

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from uuid import UUID, uuid4
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_password_usecase,
)
from password_management_context.application.use_cases import CreatePasswordUseCase
from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.domain.exceptions import PasswordManagementDomainError
from shared_kernel.access_control.exceptions import AccessDeniedError
from shared_kernel.authentication import ValidatedUser, get_current_user

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class CreatePasswordRequest(BaseModel):
    name: str
    password: str
    folder: str | None = None


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
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: CreatePasswordUseCase = Depends(get_create_password_usecase),
):
    """
    Create a new password entry.

    - **name**: Name/title for the password entry
    - **password**: The actual password to store (will be encrypted)
    - **folder**: Optional folder to organize the password
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        # Get the user's personal group
        group_repository = request.app.state.group_repository
        personal_group = group_repository.get_by_user_id(current_user.user_id)

        if not personal_group:
            raise HTTPException(
                status_code=500,
                detail="User personal group not found. Please contact support.",
            )

        password_id = uuid4()
        command = CreatePasswordCommand(
            id=password_id,
            user_id=current_user.user_id,
            group_id=personal_group.id,
            name=request_body.name,
            decrypted_password=request_body.password,
            folder=request_body.folder,
        )

        created_password_id = usecase.execute(command)

        return CreatePasswordResponse(id=created_password_id)
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

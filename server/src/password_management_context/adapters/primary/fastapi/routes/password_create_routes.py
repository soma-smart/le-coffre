from fastapi import APIRouter, HTTPException, Depends
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

router = APIRouter(prefix="/api/passwords", tags=["Password Management"])


class CreatePasswordRequest(BaseModel):
    user_id: UUID
    name: str
    password: str
    folder: str | None = None


class CreatePasswordResponse(BaseModel):
    id: UUID
    name: str
    folder: str | None = None


@router.post(
    "/",
    response_model=CreatePasswordResponse,
    status_code=201,
    summary="Create a new password",
)
def create_password(
    request: CreatePasswordRequest,
    usecase: CreatePasswordUseCase = Depends(get_create_password_usecase),
):
    """
    Create a new password entry.

    - **user_id**: ID of the user creating the password
    - **name**: Name/title for the password entry
    - **password**: The actual password to store (will be encrypted)
    - **folder**: Optional folder to organize the password
    """
    try:
        password_id = uuid4()
        command = CreatePasswordCommand(
            id=password_id,
            user_id=request.user_id,
            name=request.name,
            decrypted_password=request.password,
            folder=request.folder,
        )

        created_password_id = usecase.execute(command)

        return CreatePasswordResponse(
            id=created_password_id,
            name=request.name,
            folder=request.folder,
        )
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

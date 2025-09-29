from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_update_password_usecase,
)
from password_management_context.application.use_cases import UpdatePasswordUseCase
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.exceptions import (
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.access_control.exceptions import AccessDeniedError

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class UpdatePasswordRequest(BaseModel):
    user_id: UUID
    name: str
    password: str
    folder: str | None = None


@router.put(
    "/{password_id}",
    status_code=201,
    summary="Update an existing password",
)
def update_password(
    password_id: UUID,
    request: UpdatePasswordRequest,
    usecase: UpdatePasswordUseCase = Depends(get_update_password_usecase),
):
    """
    Update an existing password.

    - **user_id**: ID of the user asking for the password
    - **password_id**: ID of the resource
    - **name**: Name/title for the password entry
    - **password**: The actual password to store (will be encrypted)
    - **folder**: Optional folder to organize the password
    """
    try:
        command = UpdatePasswordCommand(
            requester_id=request.user_id,
            id=password_id,
            name=request.name,
            password=request.password,
            folder=request.folder,
        )

        usecase.execute(command)

    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

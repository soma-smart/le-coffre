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
    NotPasswordOwnerError,
)
from shared_kernel.domain.exceptions import AccessDeniedError
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.adapters.primary.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class UpdatePasswordRequest(BaseModel):
    name: str | None = None
    password: str | None = None
    folder: str | None = None
    login: str | None = None
    url: str | None = None


@router.put(
    "/{password_id}",
    status_code=201,
    summary="Update an existing password",
)
def update_password(
    password_id: UUID,
    request: UpdatePasswordRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdatePasswordUseCase = Depends(get_update_password_usecase),
):
    """
    Update an existing password by its ID.

    - **password_id**: ID of the resource
    - **name**: Name/title for the password entry
    - **password**: The actual password to store (will be encrypted)
    - **folder**: Optional folder to organize the password
    - **login**: Optional login/username associated with the password entry
    - **url**: Optional URL associated with the password entry
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        command = UpdatePasswordCommand(
            requester_id=current_user.user_id,
            id=password_id,
            name=request.name,
            password=request.password,
            folder=request.folder,
            login=request.login,
            url=request.url,
        )

        usecase.execute(command)

    except (PasswordNotFoundError, NotPasswordOwnerError) as e:
        # For security, treat both not found and not owner as 404
        raise HTTPException(status_code=404, detail=str(e))
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in update password")
        raise HTTPException(status_code=500, detail="Internal server error")

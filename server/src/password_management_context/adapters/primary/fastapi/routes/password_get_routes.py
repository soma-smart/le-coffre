import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_password_usecase,
)
from password_management_context.application.commands import GetPasswordCommand
from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.domain.exceptions import AccessDeniedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class GetPasswordResponse(BaseModel):
    password: str


@router.get(
    "/{password_id}",
    response_model=GetPasswordResponse,
    status_code=200,
    summary="Get a password by ID",
)
def get_password(
    password_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetPasswordUseCase = Depends(get_get_password_usecase),
):
    """
    Retrieve a password by its ID with user authentication.

    - **password_id**: The ID of the password to retrieve
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        command = GetPasswordCommand(requester_id=current_user.user_id, password_id=password_id)
        decrypted_password = usecase.execute(command)

        return GetPasswordResponse(password=decrypted_password)
    except (PasswordNotFoundError, PasswordAccessDeniedError) as e:
        # For security, treat both not found and access denied as 404
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get password")
        raise HTTPException(status_code=500, detail="Internal server error") from e

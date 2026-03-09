import logging
from datetime import datetime
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
    id: UUID
    name: str
    password: str
    login: str | None
    url: str | None
    folder: str
    created_at: datetime | None
    last_password_updated_at: datetime | None


@router.get(
    "/{password_id}",
    response_model=GetPasswordResponse,
    status_code=200,
    summary="Get a password by ID",
)
def get_password(
    password_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: GetPasswordUseCase = Depends(get_get_password_usecase),  # noqa: B008
):
    """
    Retrieve a password by its ID with user authentication.

    - **password_id**: The ID of the password to retrieve
    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        command = GetPasswordCommand(requester_id=current_user.user_id, password_id=password_id)
        password_response = usecase.execute(command)

        return GetPasswordResponse(
            id=password_response.id,
            name=password_response.name,
            password=password_response.password,
            folder=password_response.folder,
            login=password_response.login,
            url=password_response.url,
            created_at=password_response.created_at,
            last_password_updated_at=password_response.last_password_updated_at,
        )
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

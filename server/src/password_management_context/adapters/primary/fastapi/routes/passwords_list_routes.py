from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
import logging

from password_management_context.application.commands import ListPasswordsCommand
from password_management_context.application.use_cases import ListPasswordsUseCase
from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_passwords_usecase,
)
from password_management_context.domain.exceptions import (
    PasswordManagementDomainError,
    FolderNotFoundError,
)
from shared_kernel.domain.exceptions import AccessDeniedError
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.adapters.primary.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class GetPasswordListResponse(BaseModel):
    id: UUID
    name: str
    folder: str
    group_id: UUID


@router.get(
    "/list",
    status_code=200,
    response_model=list[GetPasswordListResponse],
    summary="List all passwords, optionally filtered by folder",
)
def list_passwords(
    folder: str | None = None,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListPasswordsUseCase = Depends(get_list_passwords_usecase),
):
    """
    List all passwords for the authenticated user, optionally filtered by folder.

    - **folder**: Optional folder name to filter passwords
    - **Authentication**: Requires authentication via access_token cookie

    Returns a list of passwords accessible by the user.
    """
    try:
        command = ListPasswordsCommand(requester_id=current_user.user_id, folder=folder)
        passwords = usecase.execute(command)
        return [
            GetPasswordListResponse(
                id=password.id,
                name=password.name,
                folder=password.folder,
                group_id=password.group_id,
            )
            for password in passwords
        ]
    except FolderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in list passwords")
        raise HTTPException(status_code=500, detail="Internal server error")

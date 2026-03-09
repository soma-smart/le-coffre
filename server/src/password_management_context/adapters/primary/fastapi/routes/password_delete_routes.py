import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_delete_password_usecase,
)
from password_management_context.application.commands import DeletePasswordCommand
from password_management_context.application.use_cases import DeletePasswordUseCase
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.domain.exceptions import AccessDeniedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


@router.delete(
    "/{password_id}",
    status_code=204,
    summary="Delete a password",
)
def delete_password(
    password_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: DeletePasswordUseCase = Depends(get_delete_password_usecase),  # noqa: B008
):
    """
    Delete a password by its ID.

    - **password_id**: ID of the password to delete
    - **Authentication**: Requires authentication via access_token cookie

    Returns status code 204 (No Content) on successful deletion.
    """
    try:
        command = DeletePasswordCommand(requester_id=current_user.user_id, password_id=password_id)
        usecase.execute(command)
        return
    except (PasswordNotFoundError, NotPasswordOwnerError) as e:
        # For security, treat both not found and not owner as 404
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in delete password")
        raise HTTPException(status_code=500, detail="Internal server error") from e

from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_delete_password_usecase,
)
from password_management_context.application.use_cases import DeletePasswordUseCase
from password_management_context.domain.exceptions import (
    PasswordManagementDomainError,
    PasswordNotFoundError,
)
from shared_kernel.access_control.exceptions import AccessDeniedError
from shared_kernel.authentication import ValidatedUser
from shared_kernel.authentication.dependencies import get_current_user

router = APIRouter(prefix="/passwords", tags=["Password Management"])


@router.delete(
    "/{password_id}",
    status_code=204,
    summary="Delete a password",
)
def delete_password(
    password_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: DeletePasswordUseCase = Depends(get_delete_password_usecase),
):
    """
    Delete a password entry.

    - **password_id**: ID of the password to delete
    - **Authorization**: Bearer token required
    """
    try:
        usecase.execute(current_user.user_id, password_id)
        return
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

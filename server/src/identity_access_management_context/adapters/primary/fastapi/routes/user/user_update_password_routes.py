import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_update_user_password_usecase,
)
from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.use_cases import (
    UpdateUserPasswordUseCase,
)
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
    InvalidCredentialsException,
    UserNotFoundException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

router = APIRouter(prefix="/users", tags=["User Management"])


class UpdateUserPasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.put(
    "/me/password",
    status_code=204,
    summary="Update current user's password",
)
def update_user_password(
    request: UpdateUserPasswordRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdateUserPasswordUseCase = Depends(get_update_user_password_usecase),
):
    """
    Update the authenticated user's password.

    - **old_password**: Current password for verification
    - **new_password**: New password to set
    - **Authentication**: Requires authentication via access_token cookie

    Returns status code 204 (No Content) on successful password update.

    Raises:
    - 401: If old password is incorrect
    - 404: If user not found
    """
    try:
        command = UpdateUserPasswordCommand(
            user_id=current_user.user_id,
            old_password=request.old_password,
            new_password=request.new_password,
        )
        usecase.execute(command)

    except InvalidCredentialsException as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error") from e

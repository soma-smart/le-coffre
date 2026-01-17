from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_share_access_usecase,
)
from password_management_context.application.use_cases import ShareAccessUseCase
from password_management_context.application.commands import ShareResourceCommand
from password_management_context.domain.exceptions import PasswordAccessDeniedError
from identity_access_management_context.domain.exceptions import UserNotFoundException
from shared_kernel.authentication import ValidatedUser
from shared_kernel.authentication.dependencies import get_current_user

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class SharePasswordRequest(BaseModel):
    group_id: UUID  # Changed from user_id to group_id


class SharePasswordResponse(BaseModel):
    message: str


@router.post(
    "/{password_id}/share",
    response_model=SharePasswordResponse,
    status_code=201,
    summary="Share a password with a group",
)
def share_password(
    password_id: UUID,
    request: SharePasswordRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ShareAccessUseCase = Depends(get_share_access_usecase),
):
    """
    Share a password with a group.

    - **password_id**: UUID of the password to share
    - **group_id**: UUID of the group to grant access to
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Returns status code 201 on successful sharing.
    """
    try:
        command = ShareResourceCommand(
            owner_id=current_user.user_id,
            group_id=request.group_id,
            password_id=password_id,
        )
        usecase.execute(command)

        return SharePasswordResponse(
            message=f"Password {password_id} successfully shared with group {request.group_id}"
        )
    except PasswordAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User does not exist")
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

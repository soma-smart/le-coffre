from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_share_access_usecase,
)
from rights_access_context.application.use_cases import ShareAccessUseCase
from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.domain.exceptions import (
    PermissionDeniedError,
    RightAccessDomainError,
)
from shared_kernel.domain import UserNotFoundError, AuthenticatedUser
from identity_access_management_context.adapters.primary.dependencies import (
    get_current_user,
)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class SharePasswordRequest(BaseModel):
    user_id: UUID


class SharePasswordResponse(BaseModel):
    message: str


@router.post(
    "/{password_id}/share",
    response_model=SharePasswordResponse,
    status_code=201,
    summary="Share a password with another user",
)
def share_password(
    password_id: UUID,
    request: SharePasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    usecase: ShareAccessUseCase = Depends(get_share_access_usecase),
):
    """
    Share a password with another user by granting them access.

    - **password_id**: UUID of the password to share
    - **user_id**: UUID of the user to grant access to
    - **Authorization**: Bearer token required (owner only)
    """
    try:
        command = ShareResourceCommand(
            owner_id=current_user.user_id,
            user_id=request.user_id,
            resource_id=password_id,
        )
        usecase.execute(command)

        return SharePasswordResponse(
            message=f"Password {password_id} successfully shared with user {request.user_id}"
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RightAccessDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

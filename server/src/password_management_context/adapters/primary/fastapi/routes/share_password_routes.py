import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.domain.exceptions import UserNotFoundException
from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_share_access_usecase,
)
from password_management_context.application.commands import ShareResourceCommand
from password_management_context.application.use_cases import ShareAccessUseCase
from password_management_context.domain.exceptions import (
    GroupNotFoundError,
    PasswordAccessDeniedError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class SharePasswordRequest(BaseModel):
    group_id: UUID  # Changed from user_id to group_id
    expires_at: datetime | None = None


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
    Share a password with a group, permanently or for a limited time.

    - **password_id**: UUID of the password to share
    - **group_id**: UUID of the group to grant access to
    - **expires_at**: optional date the access lapses on; omit it to share permanently
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Returns status code 201 on successful sharing.
    """
    try:
        command = ShareResourceCommand(
            owner_id=current_user.user_id,
            group_id=request.group_id,
            password_id=password_id,
            expires_at=request.expires_at,
        )
        usecase.execute(command)

        return SharePasswordResponse(
            message=f"Password {password_id} successfully shared with group {request.group_id}"
        )
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail="Password does not exist") from e
    except GroupNotFoundError as e:
        raise HTTPException(status_code=404, detail="Group does not exist") from e
    except PasswordAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except UserNotOwnerOfGroupError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail="User does not exist") from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in share password")
        raise HTTPException(status_code=500, detail="Internal server error") from e

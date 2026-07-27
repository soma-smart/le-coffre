import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_update_share_expiration_usecase,
)
from password_management_context.application.commands import UpdateShareExpirationCommand
from password_management_context.application.use_cases import UpdateShareExpirationUseCase
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    PasswordManagementDomainError,
    PasswordNotFoundError,
    ShareExpirationInPastError,
    ShareExpirationTooFarError,
    ShareNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class UpdateShareExpirationRequest(BaseModel):
    expires_at: datetime | None = None


@router.patch(
    "/{password_id}/share/{group_id}",
    status_code=204,
    summary="Change when a password share expires",
)
def update_share_expiration(
    password_id: UUID,
    group_id: UUID,
    request: UpdateShareExpirationRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdateShareExpirationUseCase = Depends(get_update_share_expiration_usecase),
):
    """
    Extend, shorten, or lift the deadline on an existing password share.

    - **password_id**: UUID of the shared password
    - **group_id**: UUID of the group whose access is being retimed
    - **expires_at**: new date the access lapses on; null makes the share permanent
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    A share that has already expired can still be extended, as long as it has not
    been purged yet.

    Returns status code 204 (No Content) on success.
    """
    try:
        command = UpdateShareExpirationCommand(
            owner_id=current_user.user_id,
            group_id=group_id,
            password_id=password_id,
            expires_at=request.expires_at,
        )
        usecase.execute(command)

        return
    except (ShareExpirationInPastError, ShareExpirationTooFarError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotPasswordOwnerError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail="Password does not exist") from e
    except ShareNotFoundError as e:
        raise HTTPException(status_code=404, detail="This group has no shared access to the password") from e
    except PasswordManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in update share expiration")
        raise HTTPException(status_code=500, detail="Internal server error") from e

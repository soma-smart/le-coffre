from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_unshare_access_usecase,
)
from password_management_context.application.use_cases import UnshareAccessUseCase
from password_management_context.application.commands import UnshareResourceCommand
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    CannotUnshareWithOwnerError,
)
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.adapters.primary.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passwords", tags=["Password Management"])


@router.delete(
    "/{password_id}/share/{group_id}",
    status_code=204,
    summary="Revoke password access from a group",
)
def unshare_password(
    password_id: UUID,
    group_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UnshareAccessUseCase = Depends(get_unshare_access_usecase),
):
    """
    Remove sharing of a password from a specific group.

    - **password_id**: UUID of the password to unshare
    - **group_id**: UUID of the group to revoke access from
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Returns status code 204 (No Content) on successful unsharing.

    Note: Cannot unshare with the owner group of the password.
    """
    try:
        command = UnshareResourceCommand(
            owner_id=current_user.user_id,
            group_id=group_id,
            password_id=password_id,
        )
        usecase.execute(command)

        return
    except PasswordAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except CannotUnshareWithOwnerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in unshare password")
        raise HTTPException(status_code=500, detail="Internal server error")

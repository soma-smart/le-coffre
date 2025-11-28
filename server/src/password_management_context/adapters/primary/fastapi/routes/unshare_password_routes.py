from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging

from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_unshare_access_usecase,
)
from rights_access_context.application.use_cases import UnshareAccessUseCase
from rights_access_context.application.commands import UnshareResourceCommand
from rights_access_context.domain.exceptions import (
    PermissionDeniedError,
    CannotUnshareWithOwnerError,
    RightAccessDomainError,
)
from shared_kernel.authentication import ValidatedUser
from shared_kernel.authentication.dependencies import get_current_user

router = APIRouter(prefix="/passwords", tags=["Password Management"])


@router.delete(
    "/{password_id}/share/{user_id}",
    status_code=204,
    summary="Revoke password access from a user",
)
def unshare_password(
    password_id: UUID,
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UnshareAccessUseCase = Depends(get_unshare_access_usecase),
):
    """
    Remove sharing of a password from a specific user.

    - **password_id**: UUID of the password to unshare
    - **user_id**: UUID of the user to revoke access from
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Returns status code 204 (No Content) on successful unsharing.

    Note: Cannot unshare with the owner of the password.
    """
    try:
        command = UnshareResourceCommand(
            owner_id=current_user.user_id,
            user_id=user_id,
            resource_id=password_id,
        )
        usecase.execute(command)

        return
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except CannotUnshareWithOwnerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RightAccessDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

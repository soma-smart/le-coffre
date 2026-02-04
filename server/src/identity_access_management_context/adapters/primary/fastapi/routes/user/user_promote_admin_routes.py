from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_promote_admin_usecase,
)
from identity_access_management_context.application.use_cases import PromoteAdminUseCase
from identity_access_management_context.application.commands import PromoteAdminCommand
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    UserAlreadyAdminException,
    IdentityAccessManagementDomainError,
)
from shared_kernel.domain.entities import ValidatedUser
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.adapters.primary.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["User Management"])


@router.post(
    "/{user_id}/promote-admin",
    status_code=204,
    summary="Promote a user to admin",
)
def promote_user_to_admin(
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: PromoteAdminUseCase = Depends(get_promote_admin_usecase),
):
    """
    Promote a user to administrator role.

    - **user_id**: UUID of the user to promote
    - **Authentication**: Requires authentication via access_token cookie
    - **Authorization**: Only administrators can promote users

    Returns status code 204 (No Content) on successful promotion.

    Raises:
    - 403: If requesting user is not an admin
    - 404: If target user does not exist
    - 400: If user is already an admin
    """
    try:
        command = PromoteAdminCommand(
            requesting_user=current_user.to_authenticated_user(),
            user_id=user_id,
        )
        usecase.execute(command)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except UserAlreadyAdminException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

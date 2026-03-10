import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_delete_group_usecase,
)
from identity_access_management_context.application.commands import DeleteGroupCommand
from identity_access_management_context.application.use_cases import DeleteGroupUseCase
from identity_access_management_context.domain.exceptions import (
    CannotDeleteGroupStillUsedException,
    CannotDeletePersonalGroupException,
    GroupNotFoundException,
    IdentityAccessManagementDomainError,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Group Management"])


@router.delete(
    "/{group_id}",
    status_code=204,
    summary="Delete a group",
)
def delete_group(
    group_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: DeleteGroupUseCase = Depends(get_delete_group_usecase),
):
    """
    Delete a group by ID.

    - **group_id**: UUID of the group to delete
    - **Authorization**: Bearer token required (access_token cookie)

    Only admins or group owners can delete a group.
    Personal groups cannot be deleted.
    Groups that are still in use (have passwords) cannot be deleted.
    """
    try:
        command = DeleteGroupCommand(
            requesting_user=current_user.to_authenticated_user(),
            group_id=group_id,
        )
        usecase.execute(command)
    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotDeletePersonalGroupException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except CannotDeleteGroupStillUsedException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in delete group")
        raise HTTPException(status_code=500, detail="Internal server error") from e

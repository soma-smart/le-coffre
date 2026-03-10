import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_update_group_usecase,
)
from identity_access_management_context.application.commands import (
    UpdateGroupCommand,
)
from identity_access_management_context.application.use_cases import (
    UpdateGroupUseCase,
)
from identity_access_management_context.domain.exceptions import (
    CannotModifyPersonalGroupException,
    GroupNotFoundException,
    IdentityAccessManagementDomainError,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities.validated_user import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Group Management"])


class UpdateGroupRequest(BaseModel):
    name: str


class UpdateGroupResponse(BaseModel):
    id: UUID
    name: str
    message: str


@router.put(
    "/{group_id}",
    status_code=200,
    response_model=UpdateGroupResponse,
    summary="Update a group",
)
def update_group(
    group_id: UUID,
    request: UpdateGroupRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdateGroupUseCase = Depends(get_update_group_usecase),
):
    """
    Update a group's name.

    - **group_id**: ID of the group to update (path parameter)
    - **name**: New name for the group
    - **Authorization**: Bearer token required (access_token cookie)
    - **Permission**: Only group owners can update groups

    Cannot update personal groups.
    Returns the updated group information.
    """
    try:
        command = UpdateGroupCommand(
            requesting_user=current_user.to_authenticated_user(),
            group_id=group_id,
            name=request.name,
        )

        usecase.execute(command)

        return UpdateGroupResponse(
            id=group_id,
            name=request.name,
            message="Group updated successfully",
        )

    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in update group")
        raise HTTPException(status_code=500, detail="Internal server error") from e

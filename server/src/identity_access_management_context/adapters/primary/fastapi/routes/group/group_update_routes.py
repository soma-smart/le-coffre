from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_update_group_usecase,
)
from identity_access_management_context.application.use_cases import (
    UpdateGroupUseCase,
)
from identity_access_management_context.application.commands import (
    UpdateGroupCommand,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
    IdentityAccessManagementDomainError,
)
from shared_kernel.authentication import ValidatedUser, get_current_user


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
            requester_id=current_user.user_id,
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
        raise HTTPException(status_code=404, detail=str(e))
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating group: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

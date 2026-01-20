from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_add_user_to_group_usecase,
)
from identity_access_management_context.application.use_cases import (
    AddUserToGroupUseCase,
)
from identity_access_management_context.application.commands import (
    AddUserToGroupCommand,
)
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
)
from shared_kernel.authentication import ValidatedUser, get_current_user


router = APIRouter(prefix="/groups", tags=["Group Management"])


class AddMemberToGroupRequest(BaseModel):
    user_id: UUID


class AddMemberToGroupResponse(BaseModel):
    group_id: UUID
    user_id: UUID
    message: str


@router.post(
    "/{group_id}/members",
    status_code=201,
    response_model=AddMemberToGroupResponse,
    summary="Add a member to a group",
)
def add_member_to_group(
    group_id: UUID,
    request: AddMemberToGroupRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: AddUserToGroupUseCase = Depends(get_add_user_to_group_usecase),
):
    """
    Add a user as a member to a group.

    - **group_id**: ID of the group (path parameter)
    - **user_id**: ID of the user to add as a member
    - **Authorization**: Bearer token required (access_token cookie)
    - **Permission**: Only group owners can add members

    The user will be added as a regular member (not an owner).
    Cannot add members to personal groups.
    Operation is idempotent - adding an existing member has no effect.
    """
    try:
        command = AddUserToGroupCommand(
            requester_id=current_user.user_id,
            group_id=group_id,
            user_id=request.user_id,
        )

        usecase.execute(command)

        return AddMemberToGroupResponse(
            group_id=group_id,
            user_id=request.user_id,
            message="Member added successfully",
        )

    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(f"Error adding member to group: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

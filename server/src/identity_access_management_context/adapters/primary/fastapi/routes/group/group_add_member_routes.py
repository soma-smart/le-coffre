import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_add_user_to_group_usecase,
)
from identity_access_management_context.application.commands import (
    AddUserToGroupCommand,
)
from identity_access_management_context.application.use_cases import (
    AddUserToGroupUseCase,
)
from identity_access_management_context.domain.exceptions import (
    CannotModifyPersonalGroupException,
    GroupNotFoundException,
    UserNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

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
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: AddUserToGroupUseCase = Depends(get_add_user_to_group_usecase),  # noqa: B008
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
        raise HTTPException(status_code=404, detail=str(e)) from e
    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in add member to group")
        raise HTTPException(status_code=500, detail="Internal server error") from e

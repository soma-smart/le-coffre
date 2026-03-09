import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_remove_user_from_group_usecase,
)
from identity_access_management_context.application.commands import (
    RemoveUserFromGroupCommand,
)
from identity_access_management_context.application.use_cases import (
    RemoveUserFromGroupUseCase,
)
from identity_access_management_context.domain.exceptions import (
    CannotModifyPersonalGroupException,
    CannotRemoveOwnerException,
    GroupNotFoundException,
    UserNotMemberOfGroupException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Group Management"])


class RemoveMemberFromGroupResponse(BaseModel):
    message: str


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=200,
    response_model=RemoveMemberFromGroupResponse,
    summary="Remove a member from a group",
)
def remove_member_from_group(
    group_id: UUID,
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: RemoveUserFromGroupUseCase = Depends(get_remove_user_from_group_usecase),  # noqa: B008
):
    """
    Remove a member from a group.

    - **group_id**: ID of the group (path parameter)
    - **user_id**: ID of the user to remove (path parameter)
    - **Authorization**: Bearer token required (access_token cookie)
    - **Permission**: Only group owners can remove members

    Cannot remove owners from groups.
    Cannot modify personal groups.
    The user to be removed must be a member of the group.
    """
    try:
        command = RemoveUserFromGroupCommand(
            requester_id=current_user.user_id,
            group_id=group_id,
            user_id=user_id,
        )

        usecase.execute(command)

        return RemoveMemberFromGroupResponse(
            message="Member removed successfully",
        )

    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except UserNotMemberOfGroupException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except CannotRemoveOwnerException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in remove member from group")
        raise HTTPException(status_code=500, detail="Internal server error") from e

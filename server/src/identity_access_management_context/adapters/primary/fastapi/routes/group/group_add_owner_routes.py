import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_add_owner_to_group_usecase,
)
from identity_access_management_context.application.commands import (
    AddOwnerToGroupCommand,
)
from identity_access_management_context.application.use_cases import (
    AddOwnerToGroupUseCase,
)
from identity_access_management_context.domain.exceptions import (
    CannotModifyPersonalGroupException,
    GroupNotFoundException,
    UserNotFoundException,
    UserNotMemberOfGroupException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Group Management"])


class AddOwnerToGroupRequest(BaseModel):
    user_id: UUID


class AddOwnerToGroupResponse(BaseModel):
    group_id: UUID
    user_id: UUID
    message: str


@router.post(
    "/{group_id}/owners",
    status_code=201,
    response_model=AddOwnerToGroupResponse,
    summary="Add an owner to a group",
)
def add_owner_to_group(
    group_id: UUID,
    request: AddOwnerToGroupRequest,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: AddOwnerToGroupUseCase = Depends(get_add_owner_to_group_usecase),  # noqa: B008
):
    """
    Promote an existing member to owner of a group.

    - **group_id**: ID of the group (path parameter)
    - **user_id**: ID of the user to promote to owner
    - **Authorization**: Bearer token required (access_token cookie)
    - **Permission**: Only group owners can add new owners

    The user must already be a member of the group before being promoted to owner.
    Cannot add owners to personal groups.
    Operation is idempotent - promoting an existing owner has no effect.
    """
    try:
        command = AddOwnerToGroupCommand(
            requester_id=current_user.user_id,
            group_id=group_id,
            user_id=request.user_id,
        )

        usecase.execute(command)

        return AddOwnerToGroupResponse(
            group_id=group_id,
            user_id=request.user_id,
            message="Owner added successfully",
        )

    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except UserNotMemberOfGroupException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in add owner to group")
        raise HTTPException(status_code=500, detail="Internal server error") from e

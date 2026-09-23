import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_demote_owner_to_member_usecase,
)
from identity_access_management_context.application.commands import (
    DemoteOwnerToMemberCommand,
)
from identity_access_management_context.application.use_cases import (
    DemoteOwnerToMemberUseCase,
)
from identity_access_management_context.domain.exceptions import (
    CannotDemoteLastOwnerException,
    CannotDemoteOtherOwnerException,
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


class DemoteOwnerToMemberResponse(BaseModel):
    message: str


@router.delete(
    "/{group_id}/owners/{user_id}",
    status_code=200,
    response_model=DemoteOwnerToMemberResponse,
    summary="Demote an owner to a regular member",
)
def demote_owner_to_member(
    group_id: UUID,
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: DemoteOwnerToMemberUseCase = Depends(get_demote_owner_to_member_usecase),
):
    """
    Demote an owner back to a regular member of a group.

    - **group_id**: ID of the group (path parameter)
    - **user_id**: ID of the owner to demote (path parameter)
    - **Authorization**: Bearer token required (access_token cookie)
    - **Permission**: Group owners can only demote themselves; only admins can demote
      an owner other than themselves

    Cannot demote the last remaining owner of a group.
    Cannot demote owners of personal groups.
    The user to be demoted must be a member of the group.
    """
    try:
        command = DemoteOwnerToMemberCommand(
            requesting_user=current_user.to_authenticated_user(),
            group_id=group_id,
            user_id=user_id,
        )

        usecase.execute(command)

        return DemoteOwnerToMemberResponse(
            message="Owner demoted to member successfully",
        )

    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UserNotOwnerOfGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotDemoteOtherOwnerException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except CannotModifyPersonalGroupException as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except UserNotMemberOfGroupException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except CannotDemoteLastOwnerException as e:
        # 409 rather than 400: distinguishes "the group's current state forbids
        # this" from a plain bad-request, so the frontend can tell this case
        # apart from UserNotMemberOfGroupException without parsing the message.
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in demote owner to member")
        raise HTTPException(status_code=500, detail="Internal server error") from e

from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_group_usecase,
)
from identity_access_management_context.application.use_cases import GetGroupUseCase
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
)
from shared_kernel.authentication import ValidatedUser, get_current_user


router = APIRouter(prefix="/groups", tags=["Group Management"])


class GetGroupResponse(BaseModel):
    id: UUID
    name: str
    is_personal: bool
    user_id: UUID | None


@router.get(
    "/{group_id}",
    status_code=200,
    response_model=GetGroupResponse,
    summary="Get a group by ID",
)
def get_group(
    group_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetGroupUseCase = Depends(get_get_group_usecase),
):
    """
    Retrieve a group by its ID.

    - **group_id**: UUID of the group to retrieve
    - **Authorization**: Bearer token required (access_token cookie)

    Returns the group details including:
    - id: The group's unique identifier
    - name: The group's name
    - is_personal: Whether this is a personal group
    - user_id: The owner user ID (for personal groups) or null (for shared groups)
    """
    try:
        group = usecase.execute(group_id)

        return GetGroupResponse(
            id=group.id,
            name=group.name,
            is_personal=group.is_personal,
            user_id=group.user_id,
        )

    except GroupNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting group {group_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

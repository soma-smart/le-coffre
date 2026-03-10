import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_create_group_usecase,
)
from identity_access_management_context.application.commands import CreateGroupCommand
from identity_access_management_context.application.use_cases import CreateGroupUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Group Management"])


class CreateGroupRequest(BaseModel):
    name: str


class CreateGroupResponse(BaseModel):
    id: UUID
    name: str
    message: str


@router.post(
    "/",
    status_code=201,
    response_model=CreateGroupResponse,
    summary="Create a new group",
)
def create_group(
    request: CreateGroupRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: CreateGroupUseCase = Depends(get_create_group_usecase),
):
    """
    Create a new group with the authenticated user as owner.

    - **name**: Name of the group to create
    - **Authorization**: Bearer token required (access_token cookie)

    The authenticated user will be automatically set as the group owner.
    Returns the created group information with generated ID.
    """
    try:
        group_id = uuid4()

        command = CreateGroupCommand(
            id=group_id,
            name=request.name,
            creator_id=current_user.user_id,
        )

        created_group_id = usecase.execute(command)

        return CreateGroupResponse(
            id=created_group_id,
            name=request.name,
            message="Group created successfully",
        )

    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in create group")
        raise HTTPException(status_code=500, detail="Internal server error") from e

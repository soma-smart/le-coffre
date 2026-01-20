from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging
from typing import List, Optional

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_user_me_usecase,
    get_group_repository,
)
from identity_access_management_context.application.use_cases import GetUserMeUseCase
from identity_access_management_context.application.commands import GetUserMeCommand
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
)
from shared_kernel.authentication import ValidatedUser
from shared_kernel.authentication.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["User Management"])


class GetUserMeResponse(BaseModel):
    id: UUID
    username: str
    email: str
    name: str
    roles: List[str]
    personal_group_id: Optional[UUID] = None  # Added for group-based permissions


@router.get(
    "/me",
    response_model=GetUserMeResponse,
    status_code=200,
    summary="Get current user information",
)
def get_user_me(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetUserMeUseCase = Depends(get_get_user_me_usecase),
    group_repository=Depends(get_group_repository),
):
    """
    Retrieve the authenticated user's information including personal group ID.

    - **Authentication**: Requires authentication via access_token cookie

    Returns the current user's profile including id, username, email, name, roles, and personal_group_id.
    """
    try:
        command = GetUserMeCommand(
            requesting_user_id=current_user.user_id,
        )
        user = usecase.execute(command)

        # Get personal group ID
        personal_group = group_repository.get_by_user_id(user.id)
        personal_group_id = personal_group.id if personal_group else None

        return GetUserMeResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            roles=user.roles,
            personal_group_id=personal_group_id,
        )
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

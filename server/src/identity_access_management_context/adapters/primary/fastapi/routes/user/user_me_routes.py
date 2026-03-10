import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_user_me_usecase,
    get_group_repository,
)
from identity_access_management_context.application.commands import GetUserMeCommand
from identity_access_management_context.application.use_cases import GetUserMeUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


class GetUserMeResponse(BaseModel):
    id: UUID
    username: str
    email: str
    name: str
    roles: list[str]
    personal_group_id: UUID | None = None  # Added for group-based permissions
    is_sso: bool  # Indicates if the user was created via SSO


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

    Returns the current user's profile including id, username, email, name, roles, personal_group_id, and is_sso.
    """
    try:
        command = GetUserMeCommand(
            requesting_user_id=current_user.user_id,
        )
        user_response = usecase.execute(command)

        # Get personal group ID
        personal_group = group_repository.get_by_user_id(user_response.id)
        personal_group_id = personal_group.id if personal_group else None

        return GetUserMeResponse(
            id=user_response.id,
            username=user_response.username,
            email=user_response.email,
            name=user_response.name,
            roles=user_response.roles,
            personal_group_id=personal_group_id,
            is_sso=user_response.is_sso,
        )
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in get user me")
        raise HTTPException(status_code=500, detail="Internal server error") from e

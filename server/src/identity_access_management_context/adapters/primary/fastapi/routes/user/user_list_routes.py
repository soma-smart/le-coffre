import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_user_usecase,
)
from identity_access_management_context.application.commands import ListUserCommand
from identity_access_management_context.application.use_cases import ListUserUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


class ListUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    name: str
    roles: list[str]


@router.get(
    "/",
    response_model=list[ListUserResponse],
    status_code=200,
    summary="List all users",
)
def list_users(
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: ListUserUseCase = Depends(get_list_user_usecase),  # noqa: B008
):
    """
    Retrieve all users.

    - **Authentication**: Requires authentication via access_token cookie

    Returns a list of all users in the system.
    """
    try:
        command = ListUserCommand(requesting_user=current_user.to_authenticated_user())
        users = usecase.execute(command)

        return [
            ListUserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                name=user.name,
                roles=user.roles,
            )
            for user in users
        ]
    except Exception as e:
        logger.exception("Unexpected error in list users")
        raise HTTPException(status_code=500, detail="Internal server error") from e

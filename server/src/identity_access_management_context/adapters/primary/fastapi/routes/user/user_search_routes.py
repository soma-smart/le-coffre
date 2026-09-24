import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_search_users_usecase,
)
from identity_access_management_context.application.commands import SearchUsersCommand
from identity_access_management_context.application.use_cases import SearchUsersUseCase
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


class SearchUserResponse(BaseModel):
    id: UUID
    username: str
    name: str


@router.get(
    "/search",
    response_model=list[SearchUserResponse],
    status_code=200,
    summary="Search users by id, name or username",
)
def search_users(
    q: str = Query(..., min_length=3, description="Search term (id/name/username substring match)"),
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: SearchUsersUseCase = Depends(get_search_users_usecase),
):
    """
    Search users whose id, name or username contains the given term.

    - **q**: Search term, at least 3 characters

    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        command = SearchUsersCommand(query=q)
        users = usecase.execute(command)

        return [
            SearchUserResponse(
                id=user.id,
                username=user.username,
                name=user.name,
            )
            for user in users
        ]
    except Exception as e:
        logger.exception("Unexpected error in search users")
        raise HTTPException(status_code=500, detail="Internal server error") from e

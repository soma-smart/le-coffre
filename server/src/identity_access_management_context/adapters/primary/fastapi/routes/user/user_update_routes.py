import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_update_user_usecase,
)
from identity_access_management_context.application.commands import UpdateUserCommand
from identity_access_management_context.application.use_cases import UpdateUserUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


class UpdateUserRequest(BaseModel):
    username: str
    email: str
    name: str


@router.put(
    "/{user_id}",
    status_code=200,
    summary="Update a user by ID",
)
def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UpdateUserUseCase = Depends(get_update_user_usecase),
):
    """
    Update a user by its ID.

    - **user_id**: The ID of the user to update
    - **username**: New username for the user
    - **email**: New email for the user
    - **password**: New password for the user (will be hashed)

    - **Authentication**: Requires authentication via access_token cookie

    Returns the updated user ID.
    """
    try:
        command = UpdateUserCommand(
            id=user_id,
            username=request.username,
            email=request.email,
            name=request.name,
        )

        updated_user_id = usecase.execute(command)
        return {"id": updated_user_id, "message": "User updated successfully"}

    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in update user")
        raise HTTPException(status_code=500, detail="Internal server error") from e

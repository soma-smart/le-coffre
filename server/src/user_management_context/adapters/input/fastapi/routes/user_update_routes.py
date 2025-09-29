from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging
from pydantic import BaseModel

from user_management_context.adapters.input.fastapi.app_dependencies import (
    get_update_user_usecase,
)
from user_management_context.application.use_cases import UpdateUserUseCase
from user_management_context.application.commands import UpdateUserCommand
from user_management_context.domain.exceptions import (
    UserNotFoundError,
)

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
    usecase: UpdateUserUseCase = Depends(get_update_user_usecase),
):
    """
    Update a user by its ID.

    - **user_id**: The ID of the user to update
    - **username**: New username for the user
    - **email**: New email for the user
    - **password**: New password for the user (will be hashed)

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
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

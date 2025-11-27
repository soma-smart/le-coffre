from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_user_usecase,
)
from identity_access_management_context.application.use_cases import GetUserUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
)
from shared_kernel.authentication import ValidatedUser, get_current_user

router = APIRouter(prefix="/users", tags=["User Management"])


class GetUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    name: str


@router.get(
    "/{user_id}",
    response_model=GetUserResponse,
    status_code=200,
    summary="Get a user by ID",
)
def get_user(
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetUserUseCase = Depends(get_get_user_usecase),
):
    """
    Retrieve a user by its ID.

    - **user_id**: The ID of the user to retrieve

    - **Authentication**: Requires authentication via access_token cookie
    """
    try:
        user_response = usecase.execute(user_id=user_id)

        return GetUserResponse(
            id=user_response.id,
            username=user_response.username,
            email=user_response.email,
            name=user_response.name,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

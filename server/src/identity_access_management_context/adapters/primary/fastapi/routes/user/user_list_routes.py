from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
import logging

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_user_usecase,
)
from identity_access_management_context.application.use_cases import ListUserUseCase

router = APIRouter(prefix="/users", tags=["User Management"])


class ListUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    name: str


@router.get(
    "/",
    response_model=list[ListUserResponse],
    status_code=200,
    summary="List all users",
)
def list_users(
    usecase: ListUserUseCase = Depends(get_list_user_usecase),
):
    """
    Retrieve all users.

    Returns a list of all users in the system.
    """
    try:
        users = usecase.execute()

        return [
            ListUserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                name=user.name,
            )
            for user in users
        ]
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

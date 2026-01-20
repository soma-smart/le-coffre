import logging
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from password_management_context.adapters.primary.fastapi.app_dependencies import (
    get_list_resource_access_usecase,
)
from pydantic import BaseModel
from password_management_context.application.use_cases import ListAccessUseCase
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from shared_kernel.authentication import ValidatedUser
from shared_kernel.authentication.dependencies import get_current_user

router = APIRouter(prefix="/passwords", tags=["Password Management"])


class PermissionEnum(str, Enum):
    READ = "read"


class UserAccessItem(BaseModel):
    user_id: UUID
    permissions: list[PermissionEnum]
    is_owner: bool


class GroupAccessItem(BaseModel):
    user_id: UUID
    permissions: list[PermissionEnum]
    is_owner: bool


class ListPasswordAccessResponse(BaseModel):
    resource_id: UUID
    user_access_list: list[UserAccessItem]
    group_access_list: list[GroupAccessItem]


@router.get(
    "/{password_id}/access",
    response_model=ListPasswordAccessResponse,
    status_code=200,
    summary="List all users who have access to a password",
)
def list_password_access(
    password_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ListAccessUseCase = Depends(get_list_resource_access_usecase),
):
    """
    List all users who have access to a specific password.

    - **password_id**: UUID of the password to query access for
    - **Authentication**: Requires authentication via access_token cookie (owner only)

    Returns a list of users with their permissions and ownership status.
    Only the owner of the password can list who has access to it.
    """
    try:
        result = usecase.execute(
            requester_id=current_user.user_id,
            password_id=password_id,
        )

        ret = ListPasswordAccessResponse(
            resource_id=password_id, user_access_list=[], group_access_list=[]
        )
        for user_access in result.user_accesses:
            ret.user_access_list.append(
                UserAccessItem(
                    user_id=user_access.user_id,
                    is_owner=user_access.is_owner,
                    permissions=[
                        PermissionEnum(perm.value) for perm in user_access.permissions
                    ],
                )
            )
        for group_access in result.group_accesses:
            ret.group_access_list.append(
                GroupAccessItem(
                    user_id=group_access.group_id,
                    is_owner=group_access.is_owner,
                    permissions=[
                        PermissionEnum(perm.value) for perm in group_access.permissions
                    ],
                )
            )
        return ret
    except PasswordAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except PasswordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")

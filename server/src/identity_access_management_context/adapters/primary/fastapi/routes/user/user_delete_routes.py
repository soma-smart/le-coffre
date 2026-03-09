import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_delete_user_usecase,
)
from identity_access_management_context.application.commands import DeleteUserCommand
from identity_access_management_context.application.use_cases import DeleteUserUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="Delete a user by ID",
)
def delete_user(
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),  # noqa: B008
    usecase: DeleteUserUseCase = Depends(get_delete_user_usecase),  # noqa: B008
):
    """
    Delete a user by its ID.

    - **Authentication**: Requires authentication via access_token cookie

    Returns status code 204 (No Content) on successful deletion.
    """
    try:
        command = DeleteUserCommand(
            requesting_user=current_user.to_authenticated_user(),
            user_id=user_id,
        )
        usecase.execute(command)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error in delete user")
        raise HTTPException(status_code=500, detail="Internal server error") from e

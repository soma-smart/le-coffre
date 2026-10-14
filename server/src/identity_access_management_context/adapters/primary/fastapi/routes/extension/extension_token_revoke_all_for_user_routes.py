import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_revoke_all_extension_tokens_for_user_usecase,
)
from identity_access_management_context.application.commands import RevokeAllExtensionTokensForUserCommand
from identity_access_management_context.application.use_cases import RevokeAllExtensionTokensForUserUseCase
from identity_access_management_context.domain.exceptions import IdentityAccessManagementDomainError
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["Browser Extension"])


class RevokeAllExtensionTokensForUserResponse(BaseModel):
    revoked_count: int


@router.delete(
    "/{user_id}/extension-tokens",
    status_code=200,
    response_model=RevokeAllExtensionTokensForUserResponse,
    summary="Disconnect every browser extension of a user (admin only)",
)
def revoke_all_extension_tokens_for_user(
    user_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeAllExtensionTokensForUserUseCase = Depends(get_revoke_all_extension_tokens_for_user_usecase),
):
    """
    Disconnect every browser extension connected to another user's account.

    - **user_id**: whose extensions to disconnect
    - **Authentication**: requires an administrator session via access_token cookie

    For an account disabled in the identity provider but still present in the vault, or a
    device its owner can no longer reach. Returns how many were still active.
    """
    try:
        revoked_count = usecase.execute(
            RevokeAllExtensionTokensForUserCommand(
                requesting_user=current_user.to_authenticated_user(),
                target_user_id=user_id,
            )
        )
        return RevokeAllExtensionTokensForUserResponse(revoked_count=revoked_count)
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while revoking a user's extension tokens")
        raise HTTPException(status_code=500, detail="Internal server error") from e

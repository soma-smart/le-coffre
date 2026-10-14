import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_revoke_all_extension_tokens_usecase,
)
from identity_access_management_context.application.commands import RevokeAllExtensionTokensCommand
from identity_access_management_context.application.use_cases import RevokeAllExtensionTokensUseCase
from identity_access_management_context.domain.exceptions import IdentityAccessManagementDomainError
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/tokens", tags=["Browser Extension"])


class RevokeAllExtensionTokensResponse(BaseModel):
    revoked_count: int


@router.delete(
    "",
    status_code=200,
    response_model=RevokeAllExtensionTokensResponse,
    summary="Disconnect every browser extension",
)
def revoke_all_extension_tokens(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeAllExtensionTokensUseCase = Depends(get_revoke_all_extension_tokens_usecase),
):
    """
    Disconnect every browser extension connected to the signed in account.

    - **Authentication**: requires authentication via access_token cookie

    Returns how many were still active. Already revoked and expired entries are left alone,
    so their original timestamps survive in the audit trail.
    """
    try:
        revoked_count = usecase.execute(RevokeAllExtensionTokensCommand(requesting_user=current_user))
        return RevokeAllExtensionTokensResponse(revoked_count=revoked_count)
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while revoking all extension tokens")
        raise HTTPException(status_code=500, detail="Internal server error") from e

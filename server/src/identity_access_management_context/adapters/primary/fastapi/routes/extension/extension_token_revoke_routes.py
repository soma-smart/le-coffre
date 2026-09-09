import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_revoke_extension_token_usecase,
)
from identity_access_management_context.application.commands import RevokeExtensionTokenCommand
from identity_access_management_context.application.use_cases import RevokeExtensionTokenUseCase
from identity_access_management_context.domain.exceptions import (
    ExtensionTokenNotFoundError,
    IdentityAccessManagementDomainError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/tokens", tags=["Browser Extension"])


@router.delete(
    "/{token_id}",
    status_code=204,
    summary="Disconnect one browser extension",
    responses={404: {"description": "No such connected extension for this account"}},
)
def revoke_extension_token(
    token_id: UUID,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: RevokeExtensionTokenUseCase = Depends(get_revoke_extension_token_usecase),
) -> None:
    """
    Disconnect one browser extension.

    - **token_id**: the connected extension to disconnect
    - **Authentication**: requires authentication via access_token cookie

    A token belonging to another account is reported as missing rather than forbidden, so
    this route cannot be used to discover which token ids exist. Revoking an already
    revoked extension succeeds without moving the original timestamp.
    """
    try:
        usecase.execute(RevokeExtensionTokenCommand(token_id=token_id, requesting_user=current_user))
    except ExtensionTokenNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while revoking an extension token")
        raise HTTPException(status_code=500, detail="Internal server error") from e

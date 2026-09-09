import logging

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_deny_extension_pairing_usecase,
)
from identity_access_management_context.application.commands import DenyExtensionPairingCommand
from identity_access_management_context.application.use_cases import DenyExtensionPairingUseCase
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingNotFoundError,
    IdentityAccessManagementDomainError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/pairing", tags=["Browser Extension"])


@router.post(
    "/{user_code}/deny",
    status_code=204,
    summary="Deny a browser-extension pairing request",
    responses={404: {"description": "The pairing is unknown or has expired"}},
)
def deny_extension_pairing(
    user_code: str,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: DenyExtensionPairingUseCase = Depends(get_deny_extension_pairing_usecase),
) -> None:
    """
    Refuse a pairing request.

    - **user_code**: the code shown in the extension
    - **Authentication**: requires authentication via access_token cookie

    A real path rather than a timeout: someone who realises they are being phished gets a
    deliberate way out, and the extension stops polling immediately instead of waiting for
    the request to expire.
    """
    try:
        usecase.execute(DenyExtensionPairingCommand(user_code=user_code, requesting_user=current_user))
    except ExtensionPairingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while denying an extension pairing")
        raise HTTPException(status_code=500, detail="Internal server error") from e

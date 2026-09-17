import logging

from fastapi import APIRouter, Depends, HTTPException

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_approve_extension_pairing_usecase,
)
from identity_access_management_context.application.commands import ApproveExtensionPairingCommand
from identity_access_management_context.application.use_cases import ApproveExtensionPairingUseCase
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingNotFoundError,
    IdentityAccessManagementDomainError,
    TooManyActiveExtensionTokensError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/pairing", tags=["Browser Extension"])


@router.post(
    "/{user_code}/approve",
    status_code=204,
    summary="Approve a browser-extension pairing request",
    responses={
        404: {"description": "The pairing is unknown or has expired"},
        409: {"description": "The account already has the maximum number of connected extensions"},
    },
)
def approve_extension_pairing(
    user_code: str,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: ApproveExtensionPairingUseCase = Depends(get_approve_extension_pairing_usecase),
) -> None:
    """
    Approve a pairing, binding it to the signed in account.

    - **user_code**: the code the user matched against their extension
    - **Authentication**: requires authentication via access_token cookie

    No credential is issued here. The token is minted when the extension redeems the pairing,
    so its plaintext never waits anywhere for the extension to collect it.
    """
    try:
        usecase.execute(ApproveExtensionPairingCommand(user_code=user_code, requesting_user=current_user))
    except ExtensionPairingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except TooManyActiveExtensionTokensError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while approving an extension pairing")
        raise HTTPException(status_code=500, detail="Internal server error") from e

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_get_extension_pairing_usecase,
)
from identity_access_management_context.application.commands import GetExtensionPairingCommand
from identity_access_management_context.application.use_cases import GetExtensionPairingUseCase
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingNotFoundError,
    IdentityAccessManagementDomainError,
)
from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/pairing", tags=["Browser Extension"])


class GetExtensionPairingResponse(BaseModel):
    user_code: str
    device_name: str
    created_at: datetime
    expires_at: datetime
    created_from_ip: str | None
    is_resolved: bool


@router.get(
    "/{user_code}",
    status_code=200,
    response_model=GetExtensionPairingResponse,
    summary="Load a pairing request for approval",
    responses={404: {"description": "The pairing is unknown or has expired"}},
)
def get_extension_pairing(
    user_code: str,
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: GetExtensionPairingUseCase = Depends(get_get_extension_pairing_usecase),
):
    """
    Load the facts the approval page needs before the user decides.

    - **user_code**: the code shown in the extension
    - **Authentication**: requires authentication via access_token cookie

    Everything returned except `device_name` is vouched for by the server. `device_name` is
    self-reported by the extension, so the page must present it as untrusted. `created_from_ip`
    matters: a foreign address is what gives away a remote attacker who started the pairing.
    """
    try:
        result = usecase.execute(GetExtensionPairingCommand(user_code=user_code, requesting_user=current_user))
        return GetExtensionPairingResponse(
            user_code=result.user_code,
            device_name=result.device_name,
            created_at=result.created_at,
            expires_at=result.expires_at,
            created_from_ip=result.created_from_ip,
            is_resolved=result.is_resolved,
        )
    except ExtensionPairingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while loading an extension pairing")
        raise HTTPException(status_code=500, detail="Internal server error") from e

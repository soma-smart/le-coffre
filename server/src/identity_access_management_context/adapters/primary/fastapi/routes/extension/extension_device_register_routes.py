import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_client_ip,
    get_start_extension_pairing_usecase,
)
from identity_access_management_context.application.commands import StartExtensionPairingCommand
from identity_access_management_context.application.use_cases import StartExtensionPairingUseCase
from identity_access_management_context.domain.exceptions import (
    IdentityAccessManagementDomainError,
    UnsupportedPkceMethodError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/device", tags=["Browser Extension"])


class RegisterExtensionDeviceRequest(BaseModel):
    code_challenge: str = Field(description="base64url(SHA-256(code_verifier))")
    code_challenge_method: str = Field(default="S256", description="Only S256 is accepted")
    device_name: str = Field(default="", description="Self-reported; shown as untrusted on the approval page")


class RegisterExtensionDeviceResponse(BaseModel):
    user_code: str
    expires_at: datetime
    poll_interval_seconds: int


@router.post(
    "",
    status_code=201,
    response_model=RegisterExtensionDeviceResponse,
    summary="Register a browser-extension pairing request",
)
def register_extension_device(
    request_body: RegisterExtensionDeviceRequest,
    client_ip: str = Depends(get_client_ip),
    usecase: StartExtensionPairingUseCase = Depends(get_start_extension_pairing_usecase),
):
    """
    Register a pairing request before the extension opens the approval tab.

    - **code_challenge**: base64url(SHA-256(code_verifier)); the verifier stays in the extension
    - **code_challenge_method**: must be `S256`, `plain` is rejected
    - **device_name**: shown on the approval page, explicitly labelled as self-reported
    - **Authentication**: none required

    The pairing this creates grants nothing on its own: approving it needs a logged in
    session, and redeeming it additionally needs the verifier. The returned `user_code` is
    what the user matches against the code shown in their extension.
    """
    try:
        result = usecase.execute(
            StartExtensionPairingCommand(
                code_challenge=request_body.code_challenge,
                code_challenge_method=request_body.code_challenge_method,
                device_name=request_body.device_name,
                created_from_ip=client_ip,
            )
        )
        return RegisterExtensionDeviceResponse(
            user_code=result.user_code,
            expires_at=result.expires_at,
            poll_interval_seconds=result.poll_interval_seconds,
        )
    except UnsupportedPkceMethodError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while registering an extension device")
        raise HTTPException(status_code=500, detail="Internal server error") from e

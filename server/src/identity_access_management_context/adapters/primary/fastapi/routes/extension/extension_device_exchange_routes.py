import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_exchange_extension_pairing_usecase,
)
from identity_access_management_context.application.commands import ExchangeExtensionPairingCommand
from identity_access_management_context.application.responses import ExchangedExtensionTokenResponse
from identity_access_management_context.application.use_cases import ExchangeExtensionPairingUseCase
from identity_access_management_context.domain.exceptions import (
    ExtensionDomainError,
    IdentityAccessManagementDomainError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension/device", tags=["Browser Extension"])

# Every unusable-pairing outcome collapses to this one message: unknown, wrong
# verifier, expired, denied, already redeemed. Mirrors the one-time link routes.
# A caller that cannot prove it owns the pairing learns nothing from the
# difference, and a caller that can gets `status: "pending"` instead.
UNUSABLE_PAIRING_DETAIL = "This pairing request is invalid or has expired"


class ExchangeExtensionDeviceRequest(BaseModel):
    user_code: str
    code_verifier: str = Field(description="The secret the extension kept when it registered")


class ExchangeExtensionDeviceResponse(BaseModel):
    """One shape for both outcomes, keyed on `status`.

    A union response model would force the generated client into a discriminated
    type for what is, from the extension's point of view, one poll loop. The
    token fields are populated only when `status` is `approved`.
    """

    status: str = Field(description="`approved` once redeemed, `pending` while awaiting approval")
    expires_at: datetime = Field(description="Pairing expiry while pending, token expiry once approved")
    poll_interval_seconds: int | None = None
    token: str | None = None
    token_id: str | None = None
    email: str | None = None
    display_name: str | None = None


@router.post(
    "/exchange",
    status_code=200,
    response_model=ExchangeExtensionDeviceResponse,
    summary="Redeem an approved pairing for a read-only token",
    responses={400: {"description": "The pairing is invalid, expired, denied or already redeemed"}},
)
def exchange_extension_device(
    request_body: ExchangeExtensionDeviceRequest,
    usecase: ExchangeExtensionPairingUseCase = Depends(get_exchange_extension_pairing_usecase),
):
    """
    Redeem an approved pairing for a read-only bearer token.

    - **user_code**: the code returned when the device registered
    - **code_verifier**: proves this is the device that started the pairing
    - **Authentication**: none required; the verifier is the credential

    Poll this until `status` is `approved`. The token is returned exactly once and only its
    SHA-256 is stored, so a caller that loses this response has to pair again.
    """
    try:
        result = usecase.execute(
            ExchangeExtensionPairingCommand(
                user_code=request_body.user_code,
                code_verifier=request_body.code_verifier,
            )
        )

        if isinstance(result, ExchangedExtensionTokenResponse):
            return ExchangeExtensionDeviceResponse(
                status="approved",
                expires_at=result.expires_at,
                token=result.token,
                token_id=str(result.token_id),
                email=result.email,
                display_name=result.display_name,
            )

        return ExchangeExtensionDeviceResponse(
            status="pending",
            expires_at=result.expires_at,
            poll_interval_seconds=result.poll_interval_seconds,
        )
    except ExtensionDomainError as e:
        raise HTTPException(status_code=400, detail=UNUSABLE_PAIRING_DETAIL) from e
    except IdentityAccessManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error while exchanging an extension pairing")
        raise HTTPException(status_code=500, detail="Internal server error") from e

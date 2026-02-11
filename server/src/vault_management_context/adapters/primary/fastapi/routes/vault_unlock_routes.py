from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_unlock_vault_usecase,
)
from vault_management_context.application.commands import UnlockVaultCommand
from vault_management_context.application.use_cases.unlock_vault_use_case import (
    UnlockVaultUseCase,
)
from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.exceptions import (
    VaultManagementDomainError,
    ShareReconstructionError,
)

router = APIRouter(prefix="/vault", tags=["Vault"])


class UnlockVaultPostRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shares": [
                    "0:abc123def456",
                    "1:def789ghi012",
                ],
            }
        }
    )

    shares: List[str] = Field(
        ...,
        min_length=1,
        description="List of share secrets (hex strings with embedded index)",
    )


class UnlockVaultPostResponse(BaseModel):
    message: str


@router.post(
    "/unlock",
    response_model=UnlockVaultPostResponse,
    status_code=200,
    summary="Unlock the vault",
)
def unlock_vault(
    request: UnlockVaultPostRequest,
    usecase: UnlockVaultUseCase = Depends(get_unlock_vault_usecase),
):
    """
    Unlock the vault using Shamir's Secret Sharing reconstruction.

    This endpoint does not require authentication as it's needed to unlock the vault
    before any user can authenticate.

    - **shares**: List of share secrets (hex strings with embedded index in format "index:hexsecret")

    Shares are added to any existing pending shares. Use DELETE /vault/unlock/clear
    to remove all pending shares before submitting new ones.

    Returns:
    - 200: Vault unlocked successfully
    - 202: Shares accepted and stored, but more shares needed to unlock
    - 400: Invalid shares or other domain error
    """
    try:
        # Create Share objects from secrets (index is embedded in secret)
        shares = [Share(share_secret) for share_secret in request.shares]
        command = UnlockVaultCommand(shares=shares)
        usecase.execute(command)
        return {"message": "Vault unlocked successfully"}
    except ShareReconstructionError:
        # Shares were stored but insufficient to unlock
        return JSONResponse(
            status_code=202,
            content={
                "message": "Shares accepted. More shares needed to unlock the vault."
            },
        )
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

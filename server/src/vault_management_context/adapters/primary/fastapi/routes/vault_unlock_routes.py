from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from typing import List

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_unlock_vault_usecase,
)
from vault_management_context.application.use_cases.unlock_vault_use_case import (
    UnlockVaultUseCase,
)
from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.exceptions import VaultManagementDomainError

router = APIRouter(prefix="/vault", tags=["Vault"])


class UnlockVaultPostRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shares": [
                    "0:abc123def456",
                    "1:def789ghi012",
                ]
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
    """
    try:
        # Create Share objects from secrets (index is embedded in secret)
        shares = [Share(share_secret) for share_secret in request.shares]
        usecase.execute(shares)
        return {"message": "Vault unlocked successfully"}
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

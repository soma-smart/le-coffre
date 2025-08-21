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

router = APIRouter(prefix="/api/vault", tags=["Vault Operations"])


class ShareRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"index": 0, "secret": "abc123def456"}}
    )

    index: int
    secret: str


class UnlockVaultPostRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shares": [
                    {"index": 0, "secret": "abc123def456"},
                    {"index": 1, "secret": "def789ghi012"},
                ]
            }
        }
    )

    shares: List[ShareRequest] = Field(
        ..., min_length=1, description="List of shares to unlock the vault"
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

    - **shares**: List of shares (index + secret) needed to reconstruct the master secret
    """
    try:
        shares = [
            Share(share_req.index, share_req.secret) for share_req in request.shares
        ]
        usecase.execute(shares)
        return {"message": "Vault unlocked successfully"}
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

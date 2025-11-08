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
from identity_access_management_context.adapters.primary.dependencies import (
    ValidatedUser,
    NotAdminError,
    get_current_user,
)

router = APIRouter(prefix="/vault", tags=["Vault"])


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
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: UnlockVaultUseCase = Depends(get_unlock_vault_usecase),
):
    """
    Unlock the vault using Shamir's Secret Sharing reconstruction.

    Only administrators can unlock the vault.

    - **shares**: List of shares (index + secret) needed to reconstruct the master secret
    - **Authorization**: Bearer token (admin role required)
    """
    try:
        shares = [
            Share(share_req.index, share_req.secret) for share_req in request.shares
        ]
        usecase.execute(shares, current_user.to_authenticated_user())
        return {"message": "Vault unlocked successfully"}
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_lock_vault_usecase,
)
from vault_management_context.application.use_cases.lock_vault_use_case import (
    LockVaultUseCase,
)
from vault_management_context.domain.exceptions import VaultManagementDomainError

router = APIRouter(prefix="/api/vault", tags=["Vault Operations"])


class LockVaultPostResponse(BaseModel):
    message: str


@router.post(
    "/lock",
    response_model=LockVaultPostResponse,
    status_code=200,
    summary="Lock the vault",
)
def lock_vault(
    usecase: LockVaultUseCase = Depends(get_lock_vault_usecase),
):
    """
    Lock the vault by clearing the decrypted key from memory.

    The vault must be unlocked to be locked again.
    """
    try:
        usecase.execute()
        return {"message": "Vault locked successfully"}
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

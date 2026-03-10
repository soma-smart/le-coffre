from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared_kernel.adapters.primary.dependencies import get_current_user
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import ValidatedUser
from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_lock_vault_usecase,
)
from vault_management_context.application.commands import LockVaultCommand
from vault_management_context.application.use_cases.lock_vault_use_case import (
    LockVaultUseCase,
)
from vault_management_context.domain.exceptions import VaultManagementDomainError

router = APIRouter(prefix="/vault", tags=["Vault"])


class LockVaultPostResponse(BaseModel):
    message: str


@router.post(
    "/lock",
    response_model=LockVaultPostResponse,
    status_code=200,
    summary="Lock the vault",
)
def lock_vault(
    current_user: ValidatedUser = Depends(get_current_user),
    usecase: LockVaultUseCase = Depends(get_lock_vault_usecase),
):
    """
    Lock the vault by clearing the decrypted key from memory.

    The vault must be unlocked to be locked again.
    Only administrators can lock the vault.

    - **Authorization**: Requires authentication via access_token cookie
    """
    try:
        command = LockVaultCommand(requesting_user=current_user.to_authenticated_user())
        usecase.execute(command)
        return {"message": "Vault locked successfully"}
    except VaultManagementDomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NotAdminError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e

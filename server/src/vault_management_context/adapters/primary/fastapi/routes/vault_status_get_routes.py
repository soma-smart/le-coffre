from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_vault_status_usecase,
)
from vault_management_context.application.responses import VaultStatus

router = APIRouter(prefix="/vault", tags=["Vault"])


class VaultStatusResponse(BaseModel):
    status: VaultStatus


@router.get(
    "/status",
    status_code=200,
    response_model=VaultStatusResponse,
    summary="Get the current status of the vault",
)
def get_vault_status(usecase=Depends(get_vault_status_usecase)):
    """
    Retrieve the current status of the vault.

    This endpoint provides information about the vault's operational state,
    NOT_SETUP, LOCKED or UNLOCKED.
    """
    try:
        status: VaultStatus = usecase.execute()
        return {"status": status}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

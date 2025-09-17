from fastapi import APIRouter, Depends, HTTPException
from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_vault_status_usecase,
)
from vault_management_context.application.responses import VaultStatus

router = APIRouter(prefix="/api/vault", tags=["Vault Status"])


@router.get(
    "/status",
    status_code=200,
    summary="Get the current status of the vault",
)
def get_vault_status(usecase=Depends(get_vault_status_usecase)):
    try:
        status: VaultStatus = usecase.execute()
        return {"status": status}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_vault_status_usecase,
)
from vault_management_context.application.commands import GetVaultStatusCommand
from vault_management_context.application.responses import VaultStatus

logger = logging.getLogger(__name__)

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
        command = GetVaultStatusCommand()
        status: VaultStatus = usecase.execute(command)
        return {"status": status}
    except Exception as e:
        logger.exception("Error getting vault status")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

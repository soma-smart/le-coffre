from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
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
    last_share_timestamp: Optional[datetime] = None


@router.get(
    "/status",
    status_code=200,
    response_model=VaultStatusResponse,
    summary="Get the current status of the vault",
)
def get_vault_status(usecase=Depends(get_vault_status_usecase)):
    """
    Retrieve the current status of the vault.

    This endpoint provides information about the vault's operational state:
    NOT_SETUP, LOCKED, PENDING_UNLOCK, or UNLOCKED.

    When status is PENDING_UNLOCK, last_share_timestamp indicates when
    the last share was submitted.
    """
    try:
        command = GetVaultStatusCommand()
        status: VaultStatus = usecase.execute(command)

        # Get timestamp if shares are pending
        last_share_timestamp = None
        if status == VaultStatus.PENDING_UNLOCK:
            last_share_timestamp = usecase.share_repository.get_last_share_timestamp()

        return {"status": status, "last_share_timestamp": last_share_timestamp}
    except Exception as e:
        logger.exception("Error getting vault status")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

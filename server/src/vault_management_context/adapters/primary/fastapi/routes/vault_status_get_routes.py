import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from vault_management_context.adapters.primary.fastapi.app_dependencies import (
    get_vault_status_usecase,
)
from vault_management_context.application.commands import GetVaultStatusCommand
from vault_management_context.application.responses import VaultStatus
from vault_management_context.domain.value_objects import UNLOCK_SESSION_ID_PATTERN, UnlockSessionId

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vault", tags=["Vault"])


class VaultStatusResponse(BaseModel):
    status: VaultStatus
    last_share_timestamp: datetime | None = None


@router.get(
    "/status",
    status_code=200,
    response_model=VaultStatusResponse,
    summary="Get the current status of the vault",
)
def get_vault_status(
    # A header rather than a query parameter: the id is polled every few seconds
    # and must stay out of access logs, since whoever knows it can add shares.
    unlock_session_id: str | None = Header(
        default=None,
        alias="X-Unlock-Session-Id",
        pattern=UNLOCK_SESSION_ID_PATTERN,
        description="Unlock session to report the progress of",
    ),
    usecase=Depends(get_vault_status_usecase),
):
    """
    Retrieve the current status of the vault.

    This endpoint provides information about the vault's operational state:
    NOT_SETUP, LOCKED, PENDING_UNLOCK, or UNLOCKED.

    PENDING_UNLOCK is only reported for the unlock session given in the
    **X-Unlock-Session-Id** header, when that session already holds shares;
    last_share_timestamp then indicates when the last share was submitted to it.
    Without a session id, a locked vault is LOCKED.
    """
    try:
        session_id = UnlockSessionId(unlock_session_id) if unlock_session_id is not None else None
        command = GetVaultStatusCommand(session_id=session_id)
        status: VaultStatus = usecase.execute(command)

        # Get timestamp if shares are pending
        last_share_timestamp = None
        if status == VaultStatus.PENDING_UNLOCK and session_id is not None:
            last_share_timestamp = usecase.share_repository.get_last_share_timestamp(session_id)

        return {"status": status, "last_share_timestamp": last_share_timestamp}
    except Exception as e:
        logger.exception("Error getting vault status")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e
